import os
from services.tts_service import generate_audio

# Pre-generate the welcome message so there is NO latency on call pickup
HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
WELCOME_TEXT = f"Welcome to {HOTEL_NAME}! It is my absolute pleasure to serve you. How may I brighten your stay today?"

print("Generating 'welcome.mp3'...")
path = generate_audio(WELCOME_TEXT, output_filename="static/welcome.mp3")

if path:
    print(f"Success! Saved to {path}")
else:
    print("Failed to generate welcome audio.")

