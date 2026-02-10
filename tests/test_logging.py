
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

def test_chat():
    print("Testing chat endpoint...")
    
    username = "Test User Log"
    # 0. Create user or get existing
    print(f"Ensuring user {username} exists...")
    real_user_id = None
    try:
        resp = requests.post(f"{BASE_URL}/users", json={"username": username})
        if resp.status_code == 200:
            data = resp.json()
            real_user_id = data["user_id"]
            print(f"User created. ID: {real_user_id}")
        elif resp.status_code == 400: # Already exists
            print("User already exists. Fetching ID...")
            resp = requests.get(f"{BASE_URL}/users")
            users = resp.json()
            for u in users:
                if u["username"] == username:
                    real_user_id = u["user_id"]
                    break
            print(f"Found existing user ID: {real_user_id}")
        else:
            print(f"User creation status: {resp.status_code}")
            
    except Exception as e:
        print(f"Failed to create/get user: {e}")
        return

    if not real_user_id:
        print("Could not get user ID.")
        return
        
    user_id = real_user_id

    # 1. Create a session
    print(f"Creating session for user {user_id}...")
    session_id = None
    try:
        url = f"{BASE_URL}/sessions/"
        resp = requests.post(url, json={"user_id": user_id})
        if resp.status_code == 404:
             print("Retrying without trailing slash...")
             url = f"{BASE_URL}/sessions"
             resp = requests.post(url, json={"user_id": user_id})
        
        if resp.status_code != 200:
            print(f"Error creating session: {resp.status_code} - {resp.text}")
            resp.raise_for_status()

        session_data = resp.json()
        session_id = session_data["session_id"]
        print(f"Session created: {session_id}")
    except Exception as e:
        print(f"Failed to create session: {e}")
        return

    # 2. Send a message
    message_text = "Hello, my name is TestUser and I like Python."
    print(f"Sending message: '{message_text}'")
    
    if not session_id:
        print("No session ID, aborting.")
        return

    try:
        resp = requests.post(f"{BASE_URL}/conversations/", json={
            "user_id": user_id,
            "session_id": session_id,
            "role": "user",
            "message_text": message_text
        })
        resp.raise_for_status()
        data = resp.json()
        print(f"Message stored. ID: {data['message_id']}")
        
        # Wait for background processing (NLP) to happen and logs to appear
        print("Waiting 10s for background processing...")
        time.sleep(10) 
        
        # Check if we got a response (though it might be async)
        resp = requests.get(f"{BASE_URL}/conversations/session/{session_id}")
        messages = resp.json()
        print(f"Total messages in session: {len(messages)}")
        for msg in messages:
            print(f"[{msg['role']}] {msg['message_text'][:100]}...")
            
    except Exception as e:
        print(f"Failed to send message: {e}")

if __name__ == "__main__":
    test_chat()
