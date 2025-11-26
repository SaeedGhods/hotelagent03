import requests

URL = "https://hotel-agent-uwpc.onrender.com/handle-speech"

# Simulate Twilio sending user speech
payload = {
    "CallSid": "TEST_SIMULATION_123",
    "SpeechResult": "Can I order a cheeseburger?"
}

print(f"Sending simulation request to {URL}...")
try:
    response = requests.post(URL, data=payload)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")

