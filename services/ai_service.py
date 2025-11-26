import os
import google.generativeai as genai
from typing import List, Dict, Optional
import json
from twilio.rest import Client
from services.guest_service import get_guest_profile, save_last_order

# In-memory storage for chat history
conversation_history: Dict[str, List[Dict[str, str]]] = {}

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Hotel Info
try:
    with open("data/hotel_info.json", "r") as f:
        HOTEL_INFO = json.load(f)
except:
    HOTEL_INFO = {"error": "Could not load hotel info"}

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.4"))

# Twilio Client for SMS
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER") # Needs to be added to Render

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
                "description": "Order food/items AND send SMS confirmation to guest.",
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
    # Personalize prompt based on guest
    guest_name = guest_profile.get("name", "Guest")
    last_order = guest_profile.get("last_order")
    
    context = f"Guest Phone: {guest_profile['phone']}\n"
    if guest_name:
        context += f"Guest Name: {guest_name}\n"
    if last_order:
        context += f"Last Order: {last_order}\n"

    return f"""
You are Aria, the Intelligent Concierge at {HOTEL_NAME}.
GOAL: Provide "Better than Human" service using Real Knowledge and Actions.

CONTEXT:
{context}
HOTEL INFO:
{json.dumps(HOTEL_INFO, indent=2)}

PERSONALITY:
- Warm, Sunny, Delightful ("It would be my pleasure!").
- If you know the guest's name, USE IT.
- If they ordered before, mention it ("Would you like the Club Sandwich again?").

OUTPUT FORMAT (JSON ONLY):
{{
  "text": "Spoken response (Max 2 sentences)",
  "language_code": "2-letter ISO code"
}}

RULES:
1. Use 'book_room_service' to order food. This sends a real SMS.
2. Use the provided HOTEL INFO for hours/menu. Do not hallucinate.
3. If they ask for Wifi, give the real password from info.
"""

def send_sms(to_number: str, body: str):
    """
    Sends an SMS via Twilio
    """
    if not TWILIO_PHONE_NUMBER:
        print("No TWILIO_PHONE_NUMBER set, skipping SMS.")
        return
    try:
        message = twilio_client.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        print(f"SMS Sent: {message.sid}")
    except Exception as e:
        print(f"Error sending SMS: {e}")

def get_ai_response(call_sid: str, user_input: str, caller_number: str) -> Dict[str, str]:
    """
    Returns {'text': ..., 'voice': ...}
    """
    try:
        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        # Load Guest Profile
        guest = get_guest_profile(caller_number)
        
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
                        # Save to history
                        save_last_order(caller_number, item)
                        # Send SMS
                        sms_body = f"Grand Hotel: Order Confirmed! {item} is on its way."
                        send_sms(caller_number, sms_body)
                        
                        text = f"I've confirmed your order for {item}. I just sent you a text message with the details!"
                    
                    elif fn.name == "check_hotel_info":
                        # The model usually has the info in context, this is just a signal
                        # Ideally we would query a vector DB here, but prompt context handles it.
                        pass

        # Fallback text
        if not text:
            text = "I'm working on that request right now."

        voice = VOICE_MAP.get(lang, "en-US-Neural2-F")
        conversation_history[call_sid] = chat.history

        return {"text": text, "voice": voice}
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return {"text": "I apologize, I'm having a moment. Could you repeat?", "voice": "en-US-Neural2-F"}

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
