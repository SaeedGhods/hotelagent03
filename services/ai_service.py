import os
import google.generativeai as genai
from typing import List, Dict, Optional
import json

# In-memory storage
conversation_history: Dict[str, List[Dict[str, str]]] = {}

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.4"))

generation_config = {
    "temperature": AI_TEMPERATURE,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 150,
    "response_mime_type": "application/json", # FORCE JSON OUTPUT
}

# Voice Mapping for Twilio
# We map the AI's detected language code to the best Twilio Neural Voice
VOICE_MAP = {
    "en": "en-US-Neural2-F", # English (US)
    "es": "es-US-Neural2-A", # Spanish (US)
    "fr": "fr-FR-Neural2-A", # French
    "de": "de-DE-Neural2-B", # German
    "it": "it-IT-Neural2-A", # Italian
    "pt": "pt-BR-Neural2-A", # Portuguese (Brazil)
    "ja": "ja-JP-Neural2-B", # Japanese
    "zh": "cmn-CN-Wavenet-A", # Chinese (Mandarin)
    "hi": "hi-IN-Neural2-A", # Hindi
}

tools = [
    {
        "function_declarations": [
            {
                "name": "book_room_service",
                "description": "Order food or items",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "item": {"type": "STRING"},
                        "quantity": {"type": "INTEGER"},
                    },
                    "required": ["item"]
                }
            }
        ]
    }
]

BASE_SYSTEM_PROMPT = f"""
You are Aria, the Warm & Sunny AI Concierge at {HOTEL_NAME}.
Your goal: Provide a "Delightful, 5-Star Experience".

PERSONALITY:
- EXTREMELY WARM, HAPPY, and POLITE. 
- Smile while you speak! Use phrases like "It would be my pleasure!" or "Absolutely!"
- Never be blunt. Instead of "What do you want?", say "How may I brighten your stay today?"

OUTPUT FORMAT:
You must respond in JSON format ONLY:
{{
  "text": "The spoken response (Keep it under 2 sentences, but make them warm!)",
  "language_code": "2-letter ISO code"
}}

RULES:
1. Detect the language the user is speaking.
2. Reply in that SAME language.
3. Set "language_code" to match.
4. Keep "text" short but SWEET.
5. If you call a tool, say something like: "I'll have that sent right up to your room!"
"""

def get_system_prompt() -> str:
    return os.getenv("SYSTEM_PROMPT_OVERRIDE", BASE_SYSTEM_PROMPT)

def get_ai_response(call_sid: str, user_input: str) -> Dict[str, str]:
    """
    Returns a dict with 'text' and 'voice_name' for Twilio.
    """
    try:
        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            generation_config=generation_config,
            system_instruction=get_system_prompt(),
            tools=tools
        )

        chat = model.start_chat(history=conversation_history[call_sid])
        response = chat.send_message(user_input)
        
        # Parse JSON response
        try:
            data = json.loads(response.text)
            text = data.get("text", "I am listening.")
            lang = data.get("language_code", "en")
        except:
            # Fallback if model forgets JSON (unlikely with response_mime_type set)
            text = response.text
            lang = "en"

        # Handle Function Calls (if any hidden inside parts, though JSON mode usually overrides this)
        # For 2.0 Flash JSON mode, it usually puts the tool output in the text if instructed.
        # But let's double check for explicit tool calls if the text is empty.
        if not text and response.parts:
             for part in response.parts:
                if part.function_call:
                    text = "I have processed your request."
        
        # Determine Voice
        voice = VOICE_MAP.get(lang, "en-US-Neural2-F")

        conversation_history[call_sid] = chat.history

        return {"text": text, "voice": voice}
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return {"text": "I apologize, I'm having trouble. Could you repeat?", "voice": "en-US-Neural2-F"}

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
