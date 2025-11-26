import os
import google.generativeai as genai
from typing import List, Dict

# In-memory storage for conversation history
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Dynamic Configuration
HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))

# Gemini Model Configuration
generation_config = {
    "temperature": AI_TEMPERATURE,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 150,
    "response_mime_type": "text/plain",
}

# Base System Prompt
BASE_SYSTEM_PROMPT = f"""
You are a top-tier, "better than human" hotel concierge agent for {HOTEL_NAME}. 
Your goal is to assist guests with room service, housekeeping, and general questions. 
You are extremely polite, efficient, warm, and empathetic. 

Capabilities:
- You can speak multiple languages. Detect the language the user is speaking and reply in that same language.
- You have access to hotel services (simulated): Room Service, Housekeeping, Front Desk, Spa Booking.
- Keep your responses CONCISE and short (1-2 sentences max) because you are speaking over the phone. Long monologues are bad for voice.
- If the user asks for something, confirm it and say it's being taken care of.

Tone: Professional, warm, 5-star service.
"""

def get_system_prompt() -> str:
    """
    Returns the system prompt, allowing for an environment variable override.
    """
    return os.getenv("SYSTEM_PROMPT_OVERRIDE", BASE_SYSTEM_PROMPT)

def get_ai_response(call_sid: str, user_input: str) -> str:
    """
    Get a response from the Google Gemini model based on user input and conversation history.
    """
    try:
        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        # Create model instance with dynamic configuration
        model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config=generation_config,
            system_instruction=get_system_prompt()
        )

        # Start chat with existing history
        chat = model.start_chat(history=conversation_history[call_sid])
        
        # Send message
        response = chat.send_message(user_input)
        
        # Update history
        conversation_history[call_sid] = chat.history

        return response.text
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "I apologize, but I'm having trouble connecting to the service right now. Please try again."

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
