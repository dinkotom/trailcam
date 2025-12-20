import sqlite3
import datetime
from .config import Config

def get_connection():
    return sqlite3.connect(Config.DB_PATH)

def init_db():
    """Initializes the database and performs cleanup."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS processed_emails (
            message_id TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Cleanup: Keep DB small but safe (60 days retention as requested)
    cutoff = datetime.datetime.now() - datetime.timedelta(days=60)
    c.execute("DELETE FROM processed_emails WHERE processed_at < ?", (cutoff,))
    
    conn.commit()
    conn.close()

def is_processed(message_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM processed_emails WHERE message_id = ?", (message_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_processed(message_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO processed_emails (message_id) VALUES (?)", (message_id,))
        conn.commit()
    finally:
        conn.close()
