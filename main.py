import os
import time
import asyncio
from fastapi import FastAPI, Form, Response, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
from services.ai_service import get_ai_response, clear_history
from services.tts_service import generate_audio

load_dotenv()

app = FastAPI()

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
VERSION = "2.1.0-ASYNC-REFACTOR" 
HOST_URL = os.getenv("HOST_URL", "https://hotel-agent-uwpc.onrender.com") 

def cleanup_static_files():
    """
    Deletes MP3 files older than 1 hour to save space.
    """
    folder = "static"
    current_time = time.time()
    for f in os.listdir(folder):
        if f == "welcome.mp3": continue # Keep the welcome message
        
        file_path = os.path.join(folder, f)
        if os.path.isfile(file_path):
            if os.path.getmtime(file_path) < current_time - 3600:
                try:
                    os.remove(file_path)
                except Exception:
                    pass

@app.on_event("startup")
async def startup_event():
    # Pre-check env vars
    pass

@app.get("/")
async def root():
    return {"message": f"Hotel Agent API is running (v{VERSION})"}

@app.post("/voice")
async def voice(From: str = Form(...), CallSid: str = Form(...)):
    clear_history(CallSid)
    response = VoiceResponse()
    
    welcome_file = "static/welcome.mp3"
    if os.path.exists(welcome_file):
         clean_host = HOST_URL.rstrip("/")
         audio_url = f"{clean_host}/{welcome_file}"
         response.play(audio_url)
    else:
         response.say(f"Welcome to {HOTEL_NAME}. How can I help?", voice="en-US-Neural2-F")
    
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    response.redirect("/voice")
    return Response(content=str(response), media_type="application/xml")

@app.post("/handle-speech")
async def handle_speech(
    background_tasks: BackgroundTasks,
    CallSid: str = Form(...), 
    From: str = Form(...), 
    SpeechResult: str = Form(None)
):
    # Schedule cleanup
    background_tasks.add_task(cleanup_static_files)
    
    response = VoiceResponse()
    
    if not SpeechResult:
        response.say("I didn't catch that.", voice="en-US-Neural2-F")
        response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
        return Response(content=str(response), media_type="application/xml")

    # Get AI response (Now Awaitable)
    ai_result = await get_ai_response(CallSid, SpeechResult, From)
    ai_text = ai_result["text"]
    
    # Generate Audio via ElevenLabs (Now Awaitable)
    audio_file_path = await generate_audio(ai_text)
    
    if audio_file_path:
        clean_host = HOST_URL.rstrip("/")
        audio_url = f"{clean_host}/{audio_file_path}"
        response.play(audio_url)
    else:
        response.say(ai_text, voice=ai_result["voice"])
    
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    
    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
