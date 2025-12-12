#!/usr/bin/env python3
"""
Quick test script to verify the Agent Messiah API
Run the server first: uvicorn app.main:app --reload
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("Testing Agent Messiah API...\n")
    
    # Test 1: Root endpoint
    print("1. Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
    
    # Test 2: Agent turn - greeting
    print("2. Testing agent greeting...")
    response = requests.post(
        f"{BASE_URL}/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "שלום",
            "history": []
        }
    )
    data = response.json()
    print(f"   Status: {response.status_code}")
    print(f"   Agent says: {data['agent_reply']}")
    print(f"   Action: {data['action']}\n")
    
    # Test 3: Who are you
    print("3. Testing 'who are you' question...")
    response = requests.post(
        f"{BASE_URL}/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "מי אתה?",
            "history": []
        }
    )
    data = response.json()
    print(f"   Agent says: {data['agent_reply']}\n")
    
    # Test 4: Not interested
    print("4. Testing 'not interested'...")
    response = requests.post(
        f"{BASE_URL}/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "לא מעוניין",
            "history": [{"user": "שלום", "agent": "היי"}]
        }
    )
    data = response.json()
    print(f"   Agent says: {data['agent_reply']}")
    print(f"   Action: {data['action']}\n")
    
    # Test 5: List meetings
    print("5. Testing meetings endpoint...")
    response = requests.get(f"{BASE_URL}/meetings")
    print(f"   Status: {response.status_code}")
    print(f"   Meetings: {len(response.json())} found\n")
    
    print("✅ All API tests completed!")

if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server.")
        print("Please start the server first:")
        print("  uvicorn app.main:app --reload")
