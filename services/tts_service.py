import os
import requests
import uuid

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Voice ID: "Rachel" (American, Calm) - customizable
# See ElevenLabs library for voice IDs
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" 

def generate_audio(text: str, output_filename: str = None) -> str:
    """
    Generates audio from text using ElevenLabs API and saves it locally.
    Returns the path to the file.
    """
    if not ELEVENLABS_API_KEY:
        print("ELEVENLABS_API_KEY not set. Skipping audio generation.")
        return None

    if not output_filename:
        output_filename = f"static/{uuid.uuid4()}.mp3"
    
    # Ensure static dir exists
    os.makedirs("static", exist_ok=True)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2", # Critical for Farsi support
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            return output_filename
        else:
            print(f"ElevenLabs Error: {response.text}")
            return None
    except Exception as e:
        print(f"Error calling ElevenLabs: {e}")
        return None

