import os
import uuid
import aiohttp # Async HTTP client
import asyncio

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Voice ID: "Sarah" (Soft, Pleasant, 5-Star Service)
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL" 

async def generate_audio(text: str, output_filename: str = None) -> str:
    """
    Generates audio from text using ElevenLabs API asynchronously.
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
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.5,
            "use_speaker_boost": True
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(output_filename, 'wb') as f:
                        f.write(content)
                    return output_filename
                else:
                    error_text = await response.text()
                    print(f"ElevenLabs Error: {error_text}")
                    return None
    except Exception as e:
        print(f"Error calling ElevenLabs: {e}")
        return None
