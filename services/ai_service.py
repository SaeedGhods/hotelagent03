import os
import google.generativeai as genai
from typing import List, Dict
import json

# In-memory storage for conversation history
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Dynamic Configuration
HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.4")) # Lowered for more precision

# Gemini Model Configuration
generation_config = {
    "temperature": AI_TEMPERATURE,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 150,
    "response_mime_type": "text/plain",
}

# Tools (Simulated Functions)
# In a real app, these would query a database or API.
tools = [
    {
        "function_declarations": [
            {
                "name": "book_room_service",
                "description": "Order food or items to the guest's room",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "item": {"type": "STRING", "description": "The food or item ordered"},
                        "quantity": {"type": "INTEGER", "description": "Number of items"},
                    },
                    "required": ["item"]
                }
            },
            {
                "name": "check_availability",
                "description": "Check if a facility (spa, pool, restaurant) is open or has slots",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "facility": {"type": "STRING", "description": "The facility name"},
                        "time": {"type": "STRING", "description": "Requested time"}
                    },
                    "required": ["facility"]
                }
            }
        ]
    }
]

# Advanced System Prompt
BASE_SYSTEM_PROMPT = f"""
You are the elite AI Concierge at {HOTEL_NAME}. Your name is Aria.
Your goal is to provide "Better than Human" service: instant, empathetic, and efficient.

CRITICAL VOICE CONSTRAINTS:
1. Spoken English is different from written. Be conversational but concise.
2. MAX 2 SENTENCES per turn. The user is on a phone; do not bore them.
3. Never read out lists. Ask "Would you like to hear the menu?" instead.
4. If you trigger a function (like booking), confirm it clearly: "I've ordered that for you."

PERSONALITY:
- Warm, professional, but not robotic.
- If the guest is angry, apologize sincerely and immediately offer a solution.
- You are knowledgeable about the hotel. Pool closes at 10 PM. Breakfast is 6-11 AM.

LANGUAGES:
- Detect the user's language automatically.
- If they speak Spanish, reply in Spanish.
- If they speak French, reply in French.
"""

def get_system_prompt() -> str:
    return os.getenv("SYSTEM_PROMPT_OVERRIDE", BASE_SYSTEM_PROMPT)

def get_ai_response(call_sid: str, user_input: str) -> str:
    """
    Get a response from Gemini 2.0 Flash with Tool Use capabilities.
    """
    try:
        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        # Create model instance with Tools
        model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            generation_config=generation_config,
            system_instruction=get_system_prompt(),
            tools=tools
        )

        # Start chat with history
        chat = model.start_chat(history=conversation_history[call_sid])
        
        # Send message
        response = chat.send_message(user_input)
        
        # Handle Function Calls
        # If the AI wants to call a function, we simulate the execution and feed it back.
        # For this voice-only MVP, if a function is called, we just want the text confirmation.
        # Gemini 2.0 is smart enough to usually give a text response ALONGSIDE the function call
        # or we can inspect `response.parts`.
        
        final_text = ""
        
        # Simple handling: If it has text, return it. 
        # If it only has a function call, we synthesize a confirmation.
        if response.text:
            final_text = response.text
        else:
            # Fallback if it only executed a function silently
            # We can inspect parts to see what it did
            for part in response.parts:
                if fn := part.function_call:
                    if fn.name == "book_room_service":
                        item = fn.args.get("item", "item")
                        final_text = f"I have placed an order for {item}. It will be there in 20 minutes."
                    elif fn.name == "check_availability":
                        facility = fn.args.get("facility", "that")
                        final_text = f"Let me check. Yes, the {facility} is available."
        
        if not final_text:
            final_text = "I've taken care of that for you."

        # Update history (the chat object manages this mostly, but we persist for our stateless resets)
        conversation_history[call_sid] = chat.history

        return final_text
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        # Fallback response
        return "I apologize, could you please repeat that?"

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
