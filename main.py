import os
from fastapi import FastAPI, Form, Response
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv
from services.ai_service import get_ai_response, clear_history
import google.generativeai as genai

load_dotenv()

app = FastAPI()

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
VERSION = "1.1.0-POLYGLOT" 

@app.get("/")
async def root():
    return {"message": f"Hotel Agent API is running (v{VERSION})"}

@app.get("/debug-models")
async def debug_models():
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return {"available_models": models}
    except Exception as e:
        return {"error": str(e)}

@app.post("/voice")
async def voice(From: str = Form(...), CallSid: str = Form(...)):
    clear_history(CallSid)
    response = VoiceResponse()
    
    # Default English Greeting
    greeting = f"Welcome to {HOTEL_NAME}. How can I help you?"
    
    # Use English Neural Voice by default
    response.say(greeting, voice="en-US-Neural2-F")
    
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

    # Get AI response (Returns Dict: {'text': '...', 'voice': '...'})
    ai_result = get_ai_response(CallSid, SpeechResult)
    
    ai_text = ai_result["text"]
    ai_voice = ai_result["voice"]
    
    # Speak back with DYNAMIC voice
    response.say(ai_text, voice=ai_voice)
    
    # Loop back
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    
    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
