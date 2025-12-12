#!/usr/bin/env python3
"""
Demo script showing LLM-based conversations with the agent.
Run this to see how natural conversations work!
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import llm_agent, leads_store
from app.config import config


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_conversation_turn(role, message):
    """Print a conversation turn."""
    if role == "user":
        print(f"\n👤 Lead: {message}")
    else:
        print(f"\n🤖 Agent: {message}")


def demo_conversation():
    """Run a demo conversation."""
    print_header("Agent Messiah - LLM Conversation Demo")
    
    # Check if OpenAI is configured
    if not config.OPENAI_API_KEY:
        print("\n⚠️  OpenAI API key not configured!")
        print("Please set OPENAI_API_KEY in your .env file")
        print("See LLM_INTEGRATION.md for setup instructions")
        return
    
    print(f"\n✓ Using OpenAI model: {config.OPENAI_MODEL}")
    print(f"✓ Agent mode: {config.AGENT_MODE}")
    
    # Get a sample lead
    lead = leads_store.get_lead_by_id(1)
    if lead:
        print(f"✓ Calling lead: {lead.name} ({lead.company})")
    
    # Initialize conversation
    conversation_history = []
    
    print_header("Conversation Start")
    
    # Demo scenario: Successful meeting booking
    demo_turns = [
        "שלום, מי אתה?",
        "נשמע מעניין, ספר לי עוד",
        "יש לנו צוות SDR אבל הם עמוסים מאוד",
        "כן, אשמח לשמוע יותר במפגש",
        "מחר ב-10 מתאים לי",
    ]
    
    for i, user_input in enumerate(demo_turns, 1):
        print(f"\n--- Turn {i} ---")
        print_conversation_turn("user", user_input)
        
        # Get agent response
        try:
            agent_reply, action, payload = llm_agent.decide_next_turn_llm(
                lead=lead,
                history=conversation_history,
                last_user_utterance=user_input
            )
            
            print_conversation_turn("agent", agent_reply)
            
            # Show action if taken
            if action:
                print(f"\n   📍 Action: {action}")
                if action == "offer_slots" and payload:
                    slots = payload.get("slots", [])
                    print(f"   📅 Offered {len(slots)} meeting slots")
                elif action == "book_meeting" and payload:
                    print(f"   ✅ Meeting booked! ID: {payload.get('meeting_id')}")
                    print(f"   🔗 Calendar: {payload.get('calendar_link')}")
                elif action == "end_call":
                    print(f"   📞 Call ended: {payload.get('reason')}")
                    break
            
            # Add to history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": agent_reply})
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Make sure your OpenAI API key is valid and has credits")
            break
    
    print_header("Conversation End")
    print(f"\n✓ Conversation had {len(conversation_history) // 2} turns")
    print("✓ Check the natural flow and context awareness!")


def interactive_mode():
    """Run interactive conversation mode."""
    print_header("Interactive Mode - Chat with the Agent")
    
    if not config.OPENAI_API_KEY:
        print("\n⚠️  OpenAI API key not configured!")
        return
    
    lead = leads_store.get_lead_by_id(1)
    print(f"\n✓ You are: {lead.name if lead else 'Anonymous'}")
    print("✓ Type your messages in Hebrew or English")
    print("✓ Type 'quit' to exit\n")
    
    conversation_history = []
    
    # Get initial greeting
    greeting = llm_agent.get_initial_greeting(lead)
    print_conversation_turn("agent", greeting)
    conversation_history.append({"role": "assistant", "content": greeting})
    
    while True:
        # Get user input
        user_input = input("\n👤 You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        try:
            # Get agent response
            agent_reply, action, payload = llm_agent.decide_next_turn_llm(
                lead=lead,
                history=conversation_history,
                last_user_utterance=user_input
            )
            
            print_conversation_turn("agent", agent_reply)
            
            # Show action
            if action:
                print(f"\n   📍 Action: {action}")
                if action == "book_meeting" and payload:
                    print(f"   ✅ Meeting booked!")
                elif action == "end_call":
                    print(f"   📞 Agent ended the call")
                    break
            
            # Update history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": agent_reply})
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            break


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Demo LLM-based conversations")
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode (chat with the agent)"
    )
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        demo_conversation()
