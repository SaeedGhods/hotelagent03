import os
from fastapi import FastAPI, Form, Response
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
from services.ai_service import get_ai_response, clear_history

load_dotenv()

app = FastAPI()

# Dynamic Configuration
HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
VOICE_NAME = os.getenv("VOICE_NAME", "alice") 
# "alice" is default, try "Polly.Joanna-Neural" for better quality

# Version Tracking
VERSION = "1.0.1"  # Increment this when you make significant changes

# Default greeting (can be overridden by env var, but we append version for testing)
DEFAULT_GREETING = f"Welcome to {HOTEL_NAME}. Version {VERSION}. How can I assist you today?"
WELCOME_MESSAGE = os.getenv("WELCOME_MESSAGE", DEFAULT_GREETING)

@app.get("/")
async def root():
    return {"message": f"Hotel Agent API is running (v{VERSION})"}

@app.post("/voice")
async def voice(From: str = Form(...), CallSid: str = Form(...)):
    """
    Handle incoming calls from Twilio.
    """
    # Clear any old history for this CallSid just in case
    clear_history(CallSid)
    
    response = VoiceResponse()
    
    # Simple greeting using configured voice and message
    # We re-fetch the env var here in case it changed, but if not set, it uses our versioned default
    current_greeting = os.getenv("WELCOME_MESSAGE", f"Welcome to {HOTEL_NAME}. Version {VERSION}. How can I assist you today?")
    
    response.say(current_greeting, voice=VOICE_NAME)
    
    # Listen for user input
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    
    # If no input, loop
    response.redirect("/voice")
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/handle-speech")
async def handle_speech(CallSid: str = Form(...), SpeechResult: str = Form(None)):
    """
    Handle the speech input from the user.
    """
    response = VoiceResponse()
    
    # Re-fetch voice setting in case it changed
    voice_name = os.getenv("VOICE_NAME", "alice")

    if not SpeechResult:
        # If silence/timeout, re-prompt
        response.say("I didn't catch that. Could you please repeat?", voice=voice_name)
        response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
        return Response(content=str(response), media_type="application/xml")

    # Get AI response
    ai_text = get_ai_response(CallSid, SpeechResult)
    
    # Speak back
    response.say(ai_text, voice=voice_name)
    
    # Loop back for more conversation
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    
    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
