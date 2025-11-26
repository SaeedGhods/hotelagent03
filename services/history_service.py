import sqlite3
from typing import Optional

DB_FILE = "hotel.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def log_call_start(call_sid: str, phone: str):
    conn = get_db_connection()
    conn.execute("INSERT OR IGNORE INTO calls (call_sid, guest_phone) VALUES (?, ?)", (call_sid, phone))
    conn.commit()
    conn.close()

def log_transcript(call_sid: str, role: str, content: str):
    conn = get_db_connection()
    conn.execute("INSERT INTO transcripts (call_sid, role, content) VALUES (?, ?, ?)", (call_sid, role, content))
    conn.commit()
    conn.close()

def get_recent_calls(limit: int = 5):
    conn = get_db_connection()
    calls = conn.execute("SELECT * FROM calls ORDER BY start_time DESC LIMIT ?", (limit,)).fetchall()
    results = []
    for call in calls:
        c = dict(call)
        # Fetch transcript lines
        lines = conn.execute("SELECT role, content FROM transcripts WHERE call_sid = ? ORDER BY timestamp ASC", (c['call_sid'],)).fetchall()
        c['transcript'] = [dict(line) for line in lines]
        results.append(c)
    conn.close()
    return results

