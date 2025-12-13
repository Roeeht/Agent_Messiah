"""
LLM-based conversational agent using OpenAI API.
Provides intelligent, natural Hebrew conversations for lead qualification and meeting booking.
"""

from typing import List, Dict, Tuple, Optional, Any
from openai import OpenAI
from app import calendar_store
from app.models import Lead
from app.config import config

# Initialize OpenAI client (will be None if API key not configured)
client = OpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None

# System prompt defining the agent's persona and capabilities
SYSTEM_PROMPT = """You are an AI sales agent named "The Agent" working for Alta.

## Company: Alta
Alta provides AI solutions for sales teams. The main product is AI agents that help SDR teams increase sales and handle inbound leads automatically.

## Your Role
You call leads by phone to:
1. Present Alta and its solution
2. Qualify if the customer has a need for the solution
3. If interested - schedule a meeting with the sales team

## Conversation Guidelines
- Be friendly but professional
- Ask short, open questions
- Listen to what the customer says
- Don't be aggressive or pushy
- If customer says "not interested" - end politely

## CRITICAL: Language Rules
- You MUST respond ONLY in English
- Your responses will be automatically translated to Hebrew for the caller
- Even if the lead's name is in Hebrew characters, respond in English
- Example: If lead name is written in non-Latin characters, say "Hi Roi!" (English) and do not include non-English characters
- All conversation history is in English
- Never output Hebrew text - only English

## Conversation Flow
1. Brief greeting + introduction: "Hi [name], I'm the agent from Alta"
2. Short value proposition: "We help companies increase sales with AI agents"
3. Qualifying question: "How do you handle inbound leads today?"
4. If interested - 1-2 more qualifying questions
5. If strong interest - offer meeting
6. Set specific time from options provided

## Tools Available
When ready to book a meeting, call offer_meeting_slots.
When customer selects time, call book_meeting with chosen time.
If customer not interested at all, call end_call.

## Important
- Don't invent information about Alta not given to you
- Keep responses short - 1-2 sentences max
- Don't discuss pricing (that's for the meeting)
- Be authentic and natural
"""

# Function definitions for OpenAI function calling
FUNCTIONS = [
    {
        "name": "offer_meeting_slots",
        "description": "Offer available meeting time slots to the lead when they show strong interest",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why you're offering slots now (e.g., 'Lead showed strong interest')"
                }
            },
            "required": ["reason"]
        }
    },
    {
        "name": "book_meeting",
        "description": "Book a specific meeting slot when the lead selects a time",
        "parameters": {
            "type": "object",
            "properties": {
                "slot_index": {
                    "type": "integer",
                    "description": "Index of the selected slot (0 or 1)"
                },
                "confirmation": {
                    "type": "string",
                    "description": "What the lead said to confirm the time"
                }
            },
            "required": ["slot_index", "confirmation"]
        }
    },
    {
        "name": "end_call",
        "description": "End the call politely when the lead is not interested or conversation is complete",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for ending (e.g., 'Not interested', 'Meeting booked', 'Wrong number')"
                }
            },
            "required": ["reason"]
        }
    }
]


def decide_next_turn_llm(
    lead: Optional[Lead],
    history: List[Dict[str, str]],
    last_user_utterance: str
) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Use OpenAI API to decide the next conversational turn.
    
    Args:
        lead: Lead object with name, company, role, etc.
        history: List of conversation turns [{"role": "assistant", "content": "..."}, {"role": "user", "content": "..."}]
        last_user_utterance: What the user just said
    
    Returns:
        Tuple of (agent_reply, action, action_payload)
        - agent_reply: What the agent says next
        - action: "offer_slots", "book_meeting", "end_call", or None
        - action_payload: Additional data for the action
    """
    
    # Build messages for OpenAI
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add context about the lead if available
    if lead:
        lead_context = f"""Current lead information:
- Name: {lead.name}
- Company: {lead.company}
- Role: {lead.role}
- Phone: {lead.phone}
"""
        if lead.notes:
            lead_context += f"- Notes: {lead.notes}\n"
        
        messages.append({"role": "system", "content": lead_context})
    
    # Add conversation history
    # Support both formats: {"role": "...", "content": "..."} and {"user": "...", "agent": "..."}
    for turn in history:
        if "role" in turn and "content" in turn:
            # OpenAI format
            messages.append({
                "role": turn["role"],
                "content": turn["content"]
            })
        elif "user" in turn and "agent" in turn:
            # Legacy format from tests - convert to OpenAI format
            messages.append({
                "role": "user",
                "content": turn["user"]
            })
            messages.append({
                "role": "assistant",
                "content": turn["agent"]
            })
    
    # Add the latest user utterance
    messages.append({
        "role": "user",
        "content": last_user_utterance
    })
    
    try:
        # Call OpenAI API with function calling
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto",
            temperature=0.7,
            max_tokens=300,
        )
        
        message = response.choices[0].message
        
        # Check if the model wants to call a function
        if message.function_call:
            function_name = message.function_call.name
            import json
            function_args = json.loads(message.function_call.arguments)
            
            if function_name == "offer_meeting_slots":
                # Get available slots
                slots = calendar_store.get_available_slots()
                slots_text = " or ".join([slot.display_text for slot in slots])
                
                agent_reply = f"Sounds great! I'd be happy to schedule a brief introduction call. I have availability {slots_text}. What works for you?"
                
                return (
                    agent_reply,
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
            
            elif function_name == "book_meeting":
                slot_index = function_args.get("slot_index", 0)
                slots = calendar_store.get_available_slots()
                
                if 0 <= slot_index < len(slots):
                    selected_slot = slots[slot_index]
                    
                    # Book the meeting
                    if lead:
                        meeting = calendar_store.book_meeting(
                            lead_id=lead.id,
                            start=selected_slot.start,
                            duration_minutes=selected_slot.duration_minutes
                        )
                        
                        agent_reply = f"Excellent! I've scheduled a meeting for you on {selected_slot.display_text}. I'll send you a calendar invitation. Looking forward to the call!"
                        
                        return (
                            agent_reply,
                            "book_meeting",
                            {
                                "meeting_id": meeting.id,
                                "start": meeting.start.isoformat(),
                                "calendar_link": meeting.calendar_link
                            }
                        )
                
                # If slot selection failed, just continue conversation
                agent_reply = "Sorry, I didn't understand which time you chose. Can I offer again?"
                return (agent_reply, None, None)
            
            elif function_name == "end_call":
                reason = function_args.get("reason", "")
                
                if "not interested" in reason.lower():
                    agent_reply = "I completely understand. If you'd like to talk in the future, I'd be happy to! Have a good day."
                elif "meeting booked" in reason.lower():
                    agent_reply = "Thank you so much! Looking forward to the call. Have a great day!"
                else:
                    agent_reply = "Thank you for your time. Have a great day!"
                
                return (agent_reply, "end_call", {"reason": reason})
        
        # No function call - just continue conversation
        agent_reply = message.content or "Sorry, I didn't understand. Can you repeat?"
        
        return (agent_reply, None, None)
    
    except Exception as e:
        # Fallback to simple response on error
        print(f"OpenAI API error: {e}")
        return (
            "Sorry, there was a small technical issue. Can you repeat what you said?",
            None,
            None
        )


def get_initial_greeting(lead: Optional[Lead]) -> str:
    """
    Generate initial greeting using LLM.
    
    Args:
        lead: Lead object
    
    Returns:
        Greeting message in English (will be translated to Hebrew at endpoint)
    """
    if not lead:
        return "Hello! I'm the agent from Alta. We help companies increase sales with AI agents. How do you handle inbound leads today?"
    
    # Use LLM to generate personalized greeting
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"""Lead information:
- Name: {lead.name}
- Company: {lead.company}
- Role: {lead.role}

Generate a short personalized greeting (1-2 sentences) in ENGLISH only. Do NOT use Hebrew."""},
        {"role": "user", "content": "Start the conversation in English"}
    ]
    
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=200,
        )
        
        return response.choices[0].message.content or f"Hi {lead.name.split()[0]}! I'm the agent from Alta. We help companies increase sales with AI agents. How do you handle inbound leads today?"
    
    except Exception as e:
        print(f"OpenAI API error in greeting: {e}")
        lead_name = lead.name.split()[0] if lead else "there"
        return f"Hi {lead_name}! I'm the agent from Alta. We help companies increase sales with AI agents. How do you handle inbound leads today?"
