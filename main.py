import os
import time
import asyncio
import logging
from fastapi import FastAPI, Form, Response, BackgroundTasks, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
from services.ai_service import get_ai_response, clear_history
from services.tts_service import generate_audio
from services.pms_service import init_db, get_db_connection

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
VERSION = "3.1.0-DASHBOARD" 
HOST_URL = os.getenv("HOST_URL", "https://hotel-agent-uwpc.onrender.com") 

@app.on_event("startup")
async def startup_event():
    init_db()
    # Pre-warm greeting
    welcome_file = "static/welcome.mp3"
    if not os.path.exists(welcome_file):
        welcome_text = f"Welcome to {HOTEL_NAME}. I am Nasrin, your intelligent concierge."
        await generate_audio(welcome_text, output_filename=welcome_file)

@app.get("/")
async def root():
    return {"message": f"Hotel Agent API is running (v{VERSION}). Go to /dashboard"}

# --- DASHBOARD ROUTES ---

@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/tickets-table")
async def get_tickets_table(request: Request):
    conn = get_db_connection()
    tickets = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    return templates.TemplateResponse("tickets_partial.html", {"request": request, "tickets": tickets})

@app.get("/api/guests-list")
async def get_guests_list(request: Request):
    conn = get_db_connection()
    guests = conn.execute("SELECT * FROM guests WHERE vip_status IN ('Platinum', 'Gold')").fetchall()
    conn.close()
    return templates.TemplateResponse("guests_partial.html", {"request": request, "guests": guests})

# --- VOICE ROUTES ---

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
         response.say(f"Welcome to {HOTEL_NAME}.", voice="en-US-Neural2-F")
    
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
    response = VoiceResponse()
    
    if not SpeechResult:
        response.say("I didn't catch that.", voice="en-US-Neural2-F")
        response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
        return Response(content=str(response), media_type="application/xml")

    ai_result = await get_ai_response(CallSid, SpeechResult, From)
    ai_text = ai_result["text"]
    should_transfer = ai_result.get("transfer", False)
    
    audio_file_path = await generate_audio(ai_text)
    
    if audio_file_path:
        clean_host = HOST_URL.rstrip("/")
        audio_url = f"{clean_host}/{audio_file_path}"
        response.play(audio_url)
    else:
        response.say(ai_text, voice=ai_result["voice"])
        
    if should_transfer:
        response.dial("+14169006975")
    else:
        response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    
    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
