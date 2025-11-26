import sqlite3
import logging
import datetime
from typing import Dict, Optional, List

DB_FILE = "hotel.db"
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initialize the database with tables and mock data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Guests Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            name TEXT,
            vip_status TEXT DEFAULT 'Standard'
        )
    ''')
    
    # Bookings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER,
            room_number TEXT,
            check_in DATE,
            check_out DATE,
            balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY(guest_id) REFERENCES guests(id)
        )
    ''')
    
    # Tickets Table (Maintenance/Housekeeping)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            type TEXT, -- 'Housekeeping', 'Engineering', 'Concierge'
            description TEXT,
            status TEXT DEFAULT 'Open', -- 'Open', 'In Progress', 'Closed'
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(booking_id) REFERENCES bookings(id)
        )
    ''')
    
    # Seed Mock Data if empty
    cursor.execute("SELECT count(*) FROM guests")
    if cursor.fetchone()[0] == 0:
        logger.info("Seeding mock data...")
        
        # Create a VIP Guest (simulating YOU)
        # Updated with real phone number
        cursor.execute("INSERT INTO guests (phone, name, vip_status) VALUES (?, ?, ?)", 
                       ("+14169006975", "Saeed Ghods", "Platinum"))
        guest_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO bookings (guest_id, room_number, check_in, check_out, balance) VALUES (?, ?, ?, ?, ?)",
                       (guest_id, "402", datetime.date.today(), datetime.date.today() + datetime.timedelta(days=3), 450.00))
                       
    conn.commit()
    conn.close()

# PMS Public API

def get_guest_details(phone: str) -> Optional[Dict]:
    conn = get_db_connection()
    guest = conn.execute("SELECT * FROM guests WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    if guest:
        return dict(guest)
    return None

def get_active_booking(phone: str) -> Optional[Dict]:
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, g.name 
        FROM bookings b 
        JOIN guests g ON b.guest_id = g.id 
        WHERE g.phone = ? AND b.status = 'Active'
    ''', (phone,)).fetchone()
    conn.close()
    if booking:
        return dict(booking)
    return None

def create_ticket(phone: str, ticket_type: str, description: str) -> str:
    booking = get_active_booking(phone)
    if not booking:
        return "No active booking found. Cannot create ticket."
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tickets (booking_id, type, description) VALUES (?, ?, ?)",
                   (booking['id'], ticket_type, description))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return f"TKT-{ticket_id}"

def get_bill_details(phone: str) -> str:
    booking = get_active_booking(phone)
    if not booking:
        return "No active booking found."
    
    return f"Room {booking['room_number']}: Current Balance is ${booking['balance']:.2f}. Includes Room Rate and Taxes."

