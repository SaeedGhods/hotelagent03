import os
from fastapi import FastAPI, Form, Response
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
from services.ai_service import get_ai_response, clear_history
from services.tts_service import generate_audio
import google.generativeai as genai

load_dotenv()

app = FastAPI()

# Mount static directory to serve audio files
app.mount("/static", StaticFiles(directory="static"), name="static")

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
VERSION = "1.2.0-ELEVENLABS" 
HOST_URL = os.getenv("HOST_URL", "https://hotel-agent-uwpc.onrender.com") # Needs to be set or auto-detected

@app.get("/")
async def root():
    return {"message": f"Hotel Agent API is running (v{VERSION})"}

@app.post("/voice")
async def voice(From: str = Form(...), CallSid: str = Form(...)):
    clear_history(CallSid)
    response = VoiceResponse()
    
    # Default English Greeting
    greeting_text = f"Welcome to {HOTEL_NAME}. How can I help you?"
    
    # Try generating audio for greeting (Optional latency hit, but consistent quality)
    # For speed on first pickup, maybe stick to Twilio or pre-generate this file.
    # Let's stick to Twilio Neural for greeting to be instant.
    response.say(greeting_text, voice="en-US-Neural2-F")
    
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    response.redirect("/voice")
    return Response(content=str(response), media_type="application/xml")

@app.post("/handle-speech")
async def handle_speech(CallSid: str = Form(...), SpeechResult: str = Form(None)):
    response = VoiceResponse()
    
    if not SpeechResult:
        response.say("I didn't catch that.", voice="en-US-Neural2-F")
        response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
        return Response(content=str(response), media_type="application/xml")

    # Get AI response
    ai_result = get_ai_response(CallSid, SpeechResult)
    ai_text = ai_result["text"]
    
    # Generate Audio via ElevenLabs
    audio_file_path = generate_audio(ai_text)
    
    if audio_file_path:
        # Convert local path to public URL
        audio_url = f"{HOST_URL}/{audio_file_path}"
        response.play(audio_url)
    else:
        # Fallback to Twilio TTS if generation failed
        response.say(ai_text, voice=ai_result["voice"])
    
    # Loop back
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    
    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
