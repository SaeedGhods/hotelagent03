import os
import google.generativeai as genai
from typing import List, Dict

# In-memory storage for conversation history
# Key: CallSid, Value: List of messages (Gemini format)
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Gemini Model Configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 150,
    "response_mime_type": "text/plain",
}

SYSTEM_PROMPT = """
You are a top-tier, "better than human" hotel concierge agent for the Grand Hotel. 
Your goal is to assist guests with room service, housekeeping, and general questions. 
You are extremely polite, efficient, warm, and empathetic. 

Capabilities:
- You can speak multiple languages. Detect the language the user is speaking and reply in that same language.
- You have access to hotel services (simulated): Room Service, Housekeeping, Front Desk, Spa Booking.
- Keep your responses CONCISE and short (1-2 sentences max) because you are speaking over the phone. Long monologues are bad for voice.
- If the user asks for something, confirm it and say it's being taken care of.

Tone: Professional, warm, 5-star service.
"""

def get_ai_response(call_sid: str, user_input: str) -> str:
    """
    Get a response from the Google Gemini model based on user input and conversation history.
    """
    try:
        # Initialize chat session if new call
        # Gemini handles history via the ChatSession object, but since our app is stateless per request
        # (FastAPI), we need to reconstruct or store the session.
        # For simplicity in this stateless environment, we will recreate the chat with history each time
        # or use a simplified approach of sending history.
        
        # NOTE: genai.ChatSession is stateful. For a production app with many concurrent calls, 
        # we'd ideally store the history object or serializable history.
        # Here we will store the raw history list and re-initialize the chat.

        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        # Create model instance
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", # Fast and capable model
            generation_config=generation_config,
            system_instruction=SYSTEM_PROMPT
        )

        # Start chat with existing history
        chat = model.start_chat(history=conversation_history[call_sid])
        
        # Send message
        response = chat.send_message(user_input)
        
        # Update our stored history with the new turn (Gemini's history format)
        # We need to manually append or just rely on the fact that we don't persist the 'chat' object.
        # Wait, 'chat.history' contains the updated history. Let's save that.
        conversation_history[call_sid] = chat.history

        return response.text
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "I apologize, but I'm having trouble connecting to the service right now. Please try again."

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
