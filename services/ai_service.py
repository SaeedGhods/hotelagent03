import os
import google.generativeai as genai
from typing import List, Dict, Optional
import json
import logging
from services.pms_service import get_active_booking, create_ticket, get_bill_details, get_guest_details

logger = logging.getLogger(__name__)

conversation_history: Dict[str, List[Dict[str, str]]] = {}

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

try:
    with open("data/hotel_info.json", "r") as f:
        HOTEL_INFO = json.load(f)
except:
    HOTEL_INFO = {}

HOTEL_NAME = os.getenv("HOTEL_NAME", "Grand Hotel")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.4"))

generation_config = {
    "temperature": AI_TEMPERATURE,
    "top_p": 0.95,
    "max_output_tokens": 150,
    "response_mime_type": "application/json",
}

VOICE_MAP = {
    "en": "en-US-Neural2-F",
    "es": "es-US-Neural2-A",
    "fr": "fr-FR-Neural2-A",
}

# DEFINING POWERFUL TOOLS
tools = [
    {
        "function_declarations": [
            {
                "name": "create_maintenance_ticket",
                "description": "Log a maintenance or housekeeping issue (AC broken, towels needed, etc).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "issue_type": {"type": "STRING", "enum": ["Housekeeping", "Engineering", "Concierge"]},
                        "description": {"type": "STRING"}
                    },
                    "required": ["issue_type", "description"]
                }
            },
            {
                "name": "check_bill",
                "description": "Check the guest's current bill/folio balance.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}, # No params needed, inferred from context
                }
            },
            {
                "name": "book_room_service",
                "description": "Order food items.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "item": {"type": "STRING"},
                        "quantity": {"type": "INTEGER"}
                    },
                    "required": ["item"]
                }
            }
        ]
    }
]

def get_system_prompt(caller_number: str) -> str:
    # Real-time PMS Lookup
    booking = get_active_booking(caller_number)
    
    if booking:
        guest_context = f"""
        GUEST IDENTIFIED: {booking['name']}
        ROOM: {booking['room_number']}
        CHECK-OUT: {booking['check_out']}
        VIP STATUS: Platinum (Mock)
        """
    else:
        guest_context = "GUEST UNIDENTIFIED (Treat as new or prospective guest)"

    return f"""
You are Aria, the Advanced AI Hotel Manager at {HOTEL_NAME}.
Your goal is to solve problems instantly using your tools.

CURRENT GUEST CONTEXT:
{guest_context}

HOTEL AMENITIES:
{json.dumps(HOTEL_INFO, indent=2)}

RULES:
1. **Identify the Guest**: Use their name naturally. "Hello Mr. Ghods, how is Room 402?"
2. **Take Action**:
   - If they say "My AC is broken", call `create_maintenance_ticket`.
   - If they say "What's my bill?", call `check_bill`.
3. **Be Concise**: 1-2 sentences max.
4. **Language**: Detect and switch automatically.

OUTPUT FORMAT (JSON):
{{
  "text": "Spoken response",
  "language_code": "2-letter ISO code"
}}
"""

async def get_ai_response(call_sid: str, user_input: str, caller_number: str) -> Dict[str, str]:
    try:
        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            generation_config=generation_config,
            system_instruction=get_system_prompt(caller_number),
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
        if response.parts:
             for part in response.parts:
                if fn := part.function_call:
                    if fn.name == "create_maintenance_ticket":
                        typ = fn.args.get("issue_type", "Concierge")
                        desc = fn.args.get("description", "Issue")
                        tkt_id = create_ticket(caller_number, typ, desc)
                        text = f"I have logged that for you. Your Ticket Number is {tkt_id}. Engineering has been notified."
                    
                    elif fn.name == "check_bill":
                        bill_info = get_bill_details(caller_number)
                        text = f"Let me pull that up. {bill_info}"

                    elif fn.name == "book_room_service":
                        item = fn.args.get("item", "Food")
                        text = f"Excellent choice. An order of {item} is being prepared for your room."

        if not text:
            text = "I'm on it."

        voice = VOICE_MAP.get(lang, "en-US-Neural2-F")
        conversation_history[call_sid] = chat.history

        return {"text": text, "voice": voice}
        
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return {"text": "I apologize, the system is updating. One moment.", "voice": "en-US-Neural2-F"}

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
