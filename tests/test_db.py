import unittest
import os
import sqlite3
import datetime
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Config before importing db
from src import config
# Use a test db path
TEST_DB = os.path.join(config.Config.BASE_DIR, 'data', 'test_processed.db')
config.Config.DB_PATH = TEST_DB

from src import db

class TestTrailcamDB(unittest.TestCase):
    def setUp(self):
        # Remove old test db
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        
    def tearDown(self):
        # Clean up
        if os.path.exists(TEST_DB):
            pass # Keep it for inspection if needed, or os.remove(TEST_DB)

    def test_init_and_cleanup(self):
        # 1. Create DB manually and insert OLD data
        conn = sqlite3.connect(TEST_DB)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE processed_emails (
                message_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP
            )
        ''')
        
        # Insert 1 recent, 1 old (61 days ago; retention is 60 days)
        recent_date = datetime.datetime.now()
        old_date = datetime.datetime.now() - datetime.timedelta(days=61)
        
        c.execute("INSERT INTO processed_emails (message_id, processed_at) VALUES (?, ?)", 
                  ("msg_recent", recent_date))
        c.execute("INSERT INTO processed_emails (message_id, processed_at) VALUES (?, ?)", 
                  ("msg_old", old_date))
        conn.commit()
        conn.close()
        
        # 2. Run init_db which should trigger cleanup
        db.init_db()
        
        # 3. Verify
        conn = sqlite3.connect(TEST_DB)
        c = conn.cursor()
        c.execute("SELECT message_id FROM processed_emails")
        rows = [r[0] for r in c.fetchall()]
        conn.close()
        
        self.assertIn("msg_recent", rows)
        self.assertNotIn("msg_old", rows)

    def test_mark_and_check(self):
        db.init_db()
        self.assertFalse(db.is_processed("new_msg"))
        db.mark_processed("new_msg")
        self.assertTrue(db.is_processed("new_msg"))
        # Verify idempotency
        db.mark_processed("new_msg")
        self.assertTrue(db.is_processed("new_msg"))

if __name__ == '__main__':
    unittest.main()
