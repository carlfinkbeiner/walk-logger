import requests
import json
from datetime import datetime

def test_sms_webhook(action):
    """Test the SMS webhook endpoint locally"""
    url = "http://localhost:8000/sms"
    
    # Simulate Twilio's POST request format
    data = {
        "Body": action,
        "From": "+1234567890",
        "To": "+0987654321"
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the Flask app is running on localhost:8000")
        return False

def test_all_actions():
    """Test all valid actions"""
    actions = ["Walk Start", "Walk End", "Poo", "Pee", "Feed"]
    
    print("🧪 Testing Walk Logger App")
    print("=" * 40)
    
    for action in actions:
        print(f"\n📱 Testing: {action}")
        success = test_sms_webhook(action)
        if success:
            print(f"✅ {action} - SUCCESS")
        else:
            print(f"❌ {action} - FAILED")
    
    # Test invalid action
    print(f"\n📱 Testing: Invalid Action")
    success = test_sms_webhook("Invalid")
    if success:
        print("✅ Invalid Action - SUCCESS (rejected as expected)")
    else:
        print("❌ Invalid Action - FAILED")

if __name__ == "__main__":
    test_all_actions() 