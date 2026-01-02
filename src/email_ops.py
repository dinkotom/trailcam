import imaplib
import smtplib
import email
import logging
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
from src.config import Config

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
    log = logging.getLogger("email_ops")
    
    # Calculate date for SINCE search (IMAP requires English months like 17-Dec-2025)
    past_date = datetime.datetime.now() - datetime.timedelta(days=days)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    date_since = f"{past_date.day}-{months[past_date.month-1]}-{past_date.year}"
    
    # Search command
    search_crit = f'(SINCE {date_since})'
    log.debug(f"IMAP Search Criteria: {search_crit}")
    
    status, messages = mail.search(None, search_crit)
    log.debug(f"IMAP Search Status: {status}, Messages: {messages}")
    
    if status != "OK":
        log.warning("No messages found or search error.")
        return []

    if not messages[0]:
        log.info("No emails found in search window.")
        return []
    
    email_ids = messages[0].split()
    log.info(f"Found {len(email_ids)} email IDs.")
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

def send_alert_email(subject, body):
    """Sends an alert email to the admin."""
    log = logging.getLogger("email_ops")
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_USER
        msg['To'] = Config.ADMIN_EMAIL
        msg['Subject'] = f"[Trailcam Alert] {subject}"

        msg.attach(MIMEText(body, 'plain'))

        # Connect to SMTP (SSL)
        server = smtplib.SMTP_SSL(Config.SMTP_SERVER, 465)
        server.login(Config.EMAIL_USER, Config.EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        log.info(f"Alert email sent to {Config.ADMIN_EMAIL}")
    except Exception as e:
        log.error(f"Failed to send alert email: {e}")
