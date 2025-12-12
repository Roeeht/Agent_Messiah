"""Agent conversation logic with rule-based English responses."""

from typing import Optional
from datetime import datetime
from app.models import Lead
from app import calendar_store


class ConversationState:
    """Track conversation state."""
    GREETING = "greeting"
    QUALIFYING = "qualifying"
    OFFERING_SLOTS = "offering_slots"
    CONFIRMING_MEETING = "confirming_meeting"
    ENDING = "ending"


def decide_next_turn(
    lead: Optional[Lead],
    history: list[dict],
    last_user_utterance: str,
) -> tuple[str, Optional[str], Optional[dict]]:
    """
    Decide the next agent response based on conversation history and user input.
    
    Returns:
        tuple: (agent_reply, action, action_payload)
        - agent_reply: English text response (will be translated to Hebrew at endpoint)
        - action: "offer_slots", "book_meeting", "end_call", or None
        - action_payload: Additional data for the action
    """
    user_input = last_user_utterance.strip().lower()
    
    # Check for "not interested" signals
    not_interested_keywords = ["not interested", "no thanks", "not now", "don't want", "not for me"]
    if any(keyword in user_input for keyword in not_interested_keywords):
        return (
            "OK, I understand. Thanks for your time! If you'd like to hear more in the future, we're here.",
            "end_call",
            None
        )
    
    # Check if this is a "who are you" question
    who_are_you_keywords = ["who are you", "what is alta", "who is this", "what do you do"]
    if any(keyword in user_input for keyword in who_are_you_keywords):
        return (
            "I'm from Alta. We build AI sales agents that help SDR and sales teams schedule meetings automatically.",
            None,
            None
        )
    
    # Determine conversation stage based on history
    conv_stage = _determine_conversation_stage(history)
    
    if conv_stage == ConversationState.GREETING:
        # Initial greeting
        lead_name = lead.name.split()[0] if lead else "there"
        return (
            f"Hi {lead_name}! I'm from Alta. We help companies increase sales with AI agents. How do you handle inbound leads today?",
            None,
            None
        )
    
    elif conv_stage == ConversationState.QUALIFYING:
        # Ask qualifying questions
        question_count = _count_qualifying_questions(history)
        
        if question_count == 0:
            return (
                "Interesting. Do you have an SDR team that handles calls?",
                None,
                None
            )
        elif question_count == 1:
            # Check if user is positive
            positive_signals = ["yes", "sure", "of course", "sounds", "interesting", "want to hear"]
            if any(signal in user_input for signal in positive_signals):
                # Move to offering slots
                slots = calendar_store.get_available_slots()
                slots_text = " or ".join([slot.display_text for slot in slots])
                
                return (
                    f"Sounds great! I'd be happy to schedule a brief introduction call. I have availability {slots_text}. What works for you?",
                    "offer_slots",
                    {
                        "slots": [
                            {
                                "start": slot.start.isoformat(),
                                "display_text": slot.display_text,
                                "duration_minutes": slot.duration_minutes
                            }
                            for slot in slots
                        ]
                    }
                )
            else:
                return (
                    "I understand. Maybe we could talk briefly about how Alta can help? It would only take 15 minutes.",
                    None,
                    None
                )
        else:
            # Too many questions, try to close
            return (
                "So what do you think? Shall we schedule a brief call?",
                None,
                None
            )
    
    elif conv_stage == ConversationState.OFFERING_SLOTS:
        # User is responding to slot offer
        # Check if they picked a slot
        time_keywords = ["10", "14", "tomorrow", "day after", "morning", "afternoon", "sunday", "monday"]
        
        if any(keyword in user_input for keyword in time_keywords):
            # User picked a slot - book it
            slots = calendar_store.get_available_slots()
            # For simplicity, book the first slot
            # In production, parse which slot they chose
            chosen_slot = slots[0]
            
            if lead:
                meeting = calendar_store.book_meeting(
                    lead_id=lead.id,
                    start=chosen_slot.start,
                    duration_minutes=chosen_slot.duration_minutes
                )
                
                return (
                    f"Excellent! I've scheduled a meeting for us on {chosen_slot.display_text}. You'll receive a confirmation email. Looking forward to the call!",
                    "book_meeting",
                    {
                        "meeting_id": meeting.id,
                        "start": meeting.start.isoformat(),
                        "calendar_link": meeting.calendar_link
                    }
                )
            else:
                return (
                    "Oops, I need a few more details to schedule. Can I get your name?",
                    None,
                    None
                )
        else:
            # Didn't pick a slot, offer again
            return (
                "No problem. Do you have another time this week that works better?",
                None,
                None
            )
    
    # Default response
    return (
        "Interesting! Tell me more.",
        None,
        None
    )


def _determine_conversation_stage(history: list[dict]) -> str:
    """Determine current conversation stage based on history."""
    if not history or len(history) == 0:
        return ConversationState.GREETING
    
    # Check if we already offered slots (check for time indicators)
    for turn in history:
        agent_msg = turn.get("agent", "")
        # Look for slot offering indicators
        if any(indicator in agent_msg for indicator in ["availability", "10:00", "14:00", "tomorrow", "day after", "schedule", "works for you"]):
            return ConversationState.OFFERING_SLOTS
    
    # Check qualifying stage
    if len(history) < 3:
        return ConversationState.QUALIFYING
    
    return ConversationState.QUALIFYING


def _count_qualifying_questions(history: list[dict]) -> int:
    """Count how many qualifying questions have been asked."""
    question_markers = ["how", "do you have", "what"]
    count = 0
    
    for turn in history:
        agent_msg = turn.get("agent", "")
        if any(marker in agent_msg for marker in question_markers):
            count += 1
    
    return count
