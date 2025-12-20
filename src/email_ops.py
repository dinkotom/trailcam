import imaplib
import email
from email.header import decode_header
import datetime
from .config import Config

def connect_imap():
    """Connects to IMAP server."""
    mail = imaplib.IMAP4_SSL(Config.IMAP_SERVER)
    mail.login(Config.EMAIL_USER, Config.EMAIL_PASS)
    return mail

def fetch_recent_emails(mail, days=1):
    """
    Fetches emails from the last N days.
    Returns a list of (uid, message_object) tuples.
    """
    mail.select("inbox")
    
    # Calculate date for SINCE search (IMAP requires English months like 17-Dec-2025)
    past_date = datetime.datetime.now() - datetime.timedelta(days=days)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    date_since = f"{past_date.day}-{months[past_date.month-1]}-{past_date.year}"
    
    # Search command
    search_crit = f'(SINCE {date_since})'
    print(f"DEBUG: IMAP Search Criteria: {search_crit}")
    
    status, messages = mail.search(None, search_crit)
    print(f"DEBUG: IMAP Search Status: {status}, Messages: {messages}")
    
    if status != "OK":
        print("No messages found or search error.")
        return []

    email_ids = messages[0].split()
    print(f"DEBUG: Found {len(email_ids)} email IDs.")
    results = []
    
    for eid in email_ids:
        # Fetch the email body
        status, msg_data = mail.fetch(eid, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                results.append((eid, msg))
                
    return results

def get_email_subject(msg):
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding if encoding else "utf-8")
    return subject

def get_email_date(msg):
    """Returns a datetime object from email."""
    date_tuple = email.utils.parsedate_tz(msg["Date"])
    if date_tuple:
        return datetime.datetime.fromtimestamp(
            email.utils.mktime_tz(date_tuple), 
            datetime.timezone.utc if date_tuple[-1] is None else datetime.timezone(datetime.timedelta(seconds=date_tuple[-1]))
        )
    return datetime.datetime.now()
