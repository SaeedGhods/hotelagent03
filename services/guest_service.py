import json
import os
from typing import Dict, Optional

DATA_FILE = "data/guests.json"

def load_guests() -> Dict:
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_guests(data: Dict):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_guest_profile(phone_number: str) -> Dict:
    """
    Retrieves guest profile or creates a default one.
    """
    guests = load_guests()
    if phone_number not in guests:
        return {
            "phone": phone_number,
            "name": None,
            "visits": 1,
            "preferences": [],
            "last_order": None
        }
    return guests[phone_number]

def update_guest_profile(phone_number: str, updates: Dict):
    """
    Updates specific fields in a guest profile.
    """
    guests = load_guests()
    if phone_number not in guests:
        guests[phone_number] = {
            "phone": phone_number,
            "name": None,
            "visits": 0, # Will be incremented
            "preferences": [],
            "last_order": None
        }
    
    # Apply updates
    for key, value in updates.items():
        guests[phone_number][key] = value
    
    # Auto-increment visits if not explicitly set
    if "visits" not in updates:
         guests[phone_number]["visits"] += 1
         
    save_guests(guests)

def save_last_order(phone_number: str, order_details: str):
    update_guest_profile(phone_number, {"last_order": order_details})

