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
                "name": "transfer_call",
                "description": "Transfer the guest to a human agent/manager.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "reason": {"type": "STRING", "description": "Reason for transfer"}
                    },
                    "required": ["reason"]
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
You are Aria, the Advanced AI Hotel Manager at {HOTEL_NAME}.
GOAL: Provide "Better than Human" service using Real Knowledge and Actions.

CURRENT GUEST CONTEXT:
{context}

HOTEL AMENITIES:
{json.dumps(HOTEL_INFO, indent=2)}

RULES:
1. **Identify the Guest**: Use their name naturally.
2. **Take Action**: Use tools for tickets/bills.
3. **Transfer**: If the guest is angry, confused, or asks for a human, use `transfer_call`.
4. **Be Concise**: 1-2 sentences max.

OUTPUT FORMAT (JSON):
{{
  "text": "Spoken response",
  "language_code": "2-letter ISO code",
  "transfer": boolean  // Set true if transferring
}}
"""

async def get_ai_response(call_sid: str, user_input: str, caller_number: str) -> Dict[str, any]:
    try:
        if call_sid not in conversation_history:
             conversation_history[call_sid] = []

        model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            generation_config=generation_config,
            system_instruction=get_system_prompt(get_guest_profile(caller_number)),
            tools=tools
        )

        chat = model.start_chat(history=conversation_history[call_sid])
        response = chat.send_message(user_input)
        
        transfer_flag = False
        
        try:
            data = json.loads(response.text)
            text = data.get("text", "")
            lang = data.get("language_code", "en")
            transfer_flag = data.get("transfer", False)
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
                        text = f"I have logged that for you. Ticket {tkt_id} created."
                    
                    elif fn.name == "check_bill":
                        bill_info = get_bill_details(caller_number)
                        text = f"{bill_info}"

                    elif fn.name == "book_room_service":
                        item = fn.args.get("item", "Food")
                        text = f"I've ordered the {item} for you."
                    
                    elif fn.name == "transfer_call":
                        transfer_flag = True
                        text = "I am connecting you to a manager right away. Please hold."

        if not text:
            text = "I'm on it."

        voice = VOICE_MAP.get(lang, "en-US-Neural2-F")
        conversation_history[call_sid] = chat.history

        return {"text": text, "voice": voice, "transfer": transfer_flag}
        
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return {"text": "I apologize, the system is updating. One moment.", "voice": "en-US-Neural2-F"}

def clear_history(call_sid: str):
    if call_sid in conversation_history:
        del conversation_history[call_sid]
