import os
import google.generativeai as genai
from typing import List, Dict, Optional
import json
import logging
from twilio.rest import Client
from services.guest_service import get_guest_profile, save_last_order

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage
conversation_history: Dict[str, List[Dict[str, str]]] = {}

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Robust Config Loading
try:
    with open("data/hotel_info.json", "r") as f:
        HOTEL_INFO = json.load(f)
except Exception as e:
    logger.error(f"Failed to load hotel_info.json: {e}")
    HOTEL_INFO = {"error": "Hotel info unavailable"}

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.4"))

# Twilio Client (Optional)
try:
    twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
except:
    twilio_client = None
    TWILIO_PHONE_NUMBER = None

generation_config = {
    "temperature": AI_TEMPERATURE,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 150,
    "response_mime_type": "application/json",
}

VOICE_MAP = {
    "en": "en-US-Neural2-F",
    "es": "es-US-Neural2-A",
    "fr": "fr-FR-Neural2-A",
    "de": "de-DE-Neural2-B",
    "it": "it-IT-Neural2-A",
    "pt": "pt-BR-Neural2-A",
    "ja": "ja-JP-Neural2-B",
    "zh": "cmn-CN-Wavenet-A",
    "hi": "hi-IN-Neural2-A",
}

tools = [
    {
        "function_declarations": [
            {
                "name": "book_room_service",
                "description": "Order food/items",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "item": {"type": "STRING", "description": "Item from menu"},
                        "quantity": {"type": "INTEGER"},
                    },
                    "required": ["item"]
                }
            },
            {
                "name": "check_hotel_info",
                "description": "Look up hotel hours, wifi, or menu items.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "What to look up"}
                    },
                    "required": ["query"]
                }
            }
        ]
    }
]

def get_system_prompt(guest_profile: Dict) -> str:
    guest_name = guest_profile.get("name", "Guest")
    last_order = guest_profile.get("last_order")
    
    context = f"Guest Phone: {guest_profile['phone']}\n"
    if guest_name:
        context += f"Guest Name: {guest_name}\n"
    if last_order:
        context += f"Last Order: {last_order}\n"

    return f"""
You are Aria, the Intelligent Concierge at {HOTEL_NAME}.
GOAL: Provide "Better than Human" service.

CONTEXT:
{context}
HOTEL INFO:
{json.dumps(HOTEL_INFO, indent=2)}

PERSONALITY:
- Warm, Sunny, Delightful ("It would be my pleasure!").
- If you know the guest's name, USE IT.
- If they ordered before, mention it.

OUTPUT FORMAT (JSON ONLY):
{{
  "text": "Spoken response (Max 2 sentences)",
  "language_code": "2-letter ISO code"
}}

RULES:
1. Use 'book_room_service' to order food.
2. Use the provided HOTEL INFO for hours/menu. Do not hallucinate.
3. If they ask for Wifi, give the real password from info.
"""

def send_sms(to_number: str, body: str):
    if not twilio_client or not TWILIO_PHONE_NUMBER:
        return
    try:
        twilio_client.messages.create(body=body, from_=TWILIO_PHONE_NUMBER, to=to_number)
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")

async def get_ai_response(call_sid: str, user_input: str, caller_number: str) -> Dict[str, str]:
    """
    Async wrapper for Gemini interaction
    """
    try:
        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        guest = get_guest_profile(caller_number)
        
        # Gemini client is synchronous by default, but fast. 
        # For true async, we'd use the async client (genai.GenerativeModel is sync).
        # However, we can wrap it or just tolerate the small delay since the TTS is the bottleneck.
        # Given the library limitations, we'll keep this sync logic wrapped in async def for now.
        
        model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            generation_config=generation_config,
            system_instruction=get_system_prompt(guest),
            tools=tools
        )

        chat = model.start_chat(history=conversation_history[call_sid])
        response = chat.send_message(user_input)
        
        try:
            data = json.loads(response.text)
            text = data.get("text", "")
            lang = data.get("language_code", "en")
        except:
            text = response.text
            lang = "en"

        # Handle Function Calls
        if not text and response.parts:
             for part in response.parts:
                if fn := part.function_call:
                    if fn.name == "book_room_service":
                        item = fn.args.get("item", "item")
                        save_last_order(caller_number, item)
                        text = f"I've confirmed your order for {item}. It will be up shortly!"
                    
                    elif fn.name == "check_hotel_info":
                        pass

        if not text:
            text = "I'm working on that request right now."

        voice = VOICE_MAP.get(lang, "en-US-Neural2-F")
        conversation_history[call_sid] = chat.history

        return {"text": text, "voice": voice}
        
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return {"text": "I apologize, I'm having a moment. Could you repeat?", "voice": "en-US-Neural2-F"}

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
