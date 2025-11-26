import os
from openai import OpenAI
from typing import List, Dict

# In-memory storage for conversation history
# Key: CallSid, Value: List of messages
conversation_history: Dict[str, List[Dict[str, str]]] = {}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    Get a response from the AI model based on user input and conversation history.
    """
    # Initialize history if new call
    if call_sid not in conversation_history:
        conversation_history[call_sid] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    
    # Add user input
    conversation_history[call_sid].append({"role": "user", "content": user_input})
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",  # Using a high-quality model for "better than human" results
            messages=conversation_history[call_sid],
            max_tokens=150,
            temperature=0.7,
        )
        
        ai_response = completion.choices[0].message.content
        
        # Add AI response to history
        conversation_history[call_sid].append({"role": "assistant", "content": ai_response})
        
        return ai_response
        
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return "I apologize, but I'm having trouble connecting to the service right now. Please try again."

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]

