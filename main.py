import os
from fastapi import FastAPI, Form, Response
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
from services.ai_service import get_ai_response, clear_history
import google.generativeai as genai

load_dotenv()

app = FastAPI()

# Dynamic Configuration
HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
VOICE_NAME = os.getenv("VOICE_NAME", "alice") 

# Version Tracking
VERSION = "1.0.2-DEBUG" 

# Default greeting
DEFAULT_GREETING = f"Welcome to {HOTEL_NAME}. Version {VERSION}. How can I assist you today?"
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", DEFAULT_GREETING)

@app.get("/")
async def root():
    return {"message": f"Hotel Agent API is running (v{VERSION})"}

@app.get("/debug-models")
async def debug_models():
    """
    Debug endpoint to list available Gemini models
    """
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        return {"available_models": models}
    except Exception as e:
        return {"error": str(e)}

@app.post("/voice")
async def voice(From: str = Form(...), CallSid: str = Form(...)):
    """
    Handle incoming calls from Twilio.
    """
    clear_history(CallSid)
    response = VoiceResponse()
    current_greeting = os.getenv("WELCOME_MESSAGE", f"Welcome to {HOTEL_NAME}. Version {VERSION}. How can I assist you today?")
    response.say(current_greeting, voice=VOICE_NAME)
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    response.redirect("/voice")
    return Response(content=str(response), media_type="application/xml")

@app.post("/handle-speech")
async def handle_speech(CallSid: str = Form(...), SpeechResult: str = Form(None)):
    """
    Handle the speech input from the user.
    """
    response = VoiceResponse()
    voice_name = os.getenv("VOICE_NAME", "alice")

    if not SpeechResult:
        response.say("I didn't catch that. Could you please repeat?", voice=voice_name)
        response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
        return Response(content=str(response), media_type="application/xml")

    # Get AI response
    ai_text = get_ai_response(CallSid, SpeechResult)
    
    response.say(ai_text, voice=voice_name)
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
