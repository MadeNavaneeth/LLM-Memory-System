
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

def test_conversation():
    print(f"Testing conversation endpoint at {BASE_URL}...")
    
    # 1. Create a user
    print("\n1. Creating user...")
    try:
        user_resp = requests.post(f"{BASE_URL}/users", json={"username": "test_user_123"})
        if user_resp.status_code == 200:
            user = user_resp.json()
            user_id = user['user_id']
            print(f"✓ User created: {user['username']} ({user_id})")
        else:
            print(f"✗ Failed to create user: {user_resp.text}")
            return
    except Exception as e:
        print(f"✗ Exception creating user: {e}")
        return

    # 2. Get active session
    print("\n2. Getting session...")
    try:
        session_resp = requests.post(f"{BASE_URL}/sessions/user/{user_id}")
        # Note: API might be different, let's try getting active session
        if session_resp.status_code != 200:
             session_resp = requests.get(f"{BASE_URL}/sessions/user/{user_id}/active")
        
        if session_resp.status_code == 200:
            session = session_resp.json()
            session_id = session['session_id']
            print(f"✓ Session retrieved: {session_id}")
        else:
            print(f"✗ Failed to get session: {session_resp.text}")
            return
    except Exception as e:
        print(f"✗ Exception getting session: {e}")
        return

    # 3. Send message
    print("\n3. Sending message...")
    try:
        msg_data = {
            "user_id": user_id,
            "session_id": session_id,
            "role": "user",
            "message_text": "Hello, can you help me?"
        }
        msg_resp = requests.post(f"{BASE_URL}/conversations/", json=msg_data)
        
        if msg_resp.status_code == 200:
            print(f"✓ Message sent successfully!")
            resp_data = msg_resp.json()
            print(f"Response: {json.dumps(resp_data, indent=2)}")
        else:
            print(f"✗ Failed to send message: {msg_resp.status_code} - {msg_resp.text}")
    except Exception as e:
        print(f"✗ Exception sending message: {e}")

if __name__ == "__main__":
    test_conversation()
