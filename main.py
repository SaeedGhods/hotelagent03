import os
from fastapi import FastAPI, Form, Response
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv

load_dotenv()

from services.ai_service import get_ai_response, clear_history

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hotel Agent API is running"}

@app.post("/voice")
async def voice(From: str = Form(...), CallSid: str = Form(...)):
    """
    Handle incoming calls from Twilio.
    """
    # Clear any old history for this CallSid just in case
    clear_history(CallSid)
    
    response = VoiceResponse()
    
    # Simple greeting
    greeting = "Welcome to the Grand Hotel. How can I assist you today?"
    # We can also add this greeting to the history so the AI knows it started
    # (Optional, but good for context)
    
    response.say(greeting, voice="alice")
    
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
    
    if not SpeechResult:
        # If silence/timeout, re-prompt
        response.say("I didn't catch that. Could you please repeat?", voice="alice")
        response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
        return Response(content=str(response), media_type="application/xml")

    # Get AI response
    ai_text = get_ai_response(CallSid, SpeechResult)
    
    # Speak back
    # Note: voice="alice" is a placeholder. Twilio has Neural voices that are better.
    # We can let the AI decide the language, but Twilio <Say> needs a language code for best results.
    # For now, we'll stick to default or try to detect.
    # OpenAI GPT-4o is good at outputting text, but we need to tell Twilio how to pronounce it if it's mixed.
    # However, Twilio's standard voices are decent at auto-detect if the text is clearly one language.
    
    response.say(ai_text, voice="alice")
    
    # Loop back for more conversation
    response.gather(input="speech", action="/handle-speech", timeout=3, language="auto")
    
    return Response(content=str(response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

