import requests
import sys
import json

def verify_stream_events():
    url = "http://127.0.0.1:8002/api/v1/agent/stream_events"
    print(f"Checking POST {url}...")
    
    # Payload
    payload = {
        "input": {"messages": [{"role": "user", "content": "hi"}]},
        "config": {"configurable": {"thread_id": "test_thread"}},
        "version": "v2"
    }
    
    # Case 1: No Auth Header (Should pass with Fallback)
    print("\nCase 1: No Auth Header")
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Success! Request accepted (No Auth).")
        elif response.status_code == 403:
            print("Failed: 403 Forbidden.")
        else:
            print(f"Status: {response.status_code}. Response: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")

    # Case 2: Invalid Auth Header (Should pass with new logic)
    print("\nCase 2: Invalid Auth Header")
    headers = {"X-API-Key": "invalid-key-123"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("Success! Request accepted (Invalid Auth Fallback).")
        elif response.status_code == 403:
            print("Failed: 403 Forbidden (Logic not working).")
        else:
            print(f"Status: {response.status_code}. Response: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_stream_events()
