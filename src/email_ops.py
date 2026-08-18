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

def _search_recent(mail, days):
    """Returns IMAP ids of messages received in the last N days."""
    mail.select("inbox")
    log = logging.getLogger("email_ops")

    # Calculate date for SINCE search (IMAP requires English months like 17-Dec-2025)
    past_date = datetime.datetime.now() - datetime.timedelta(days=days)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    date_since = f"{past_date.day}-{months[past_date.month-1]}-{past_date.year}"

    search_crit = f'(SINCE {date_since})'
    log.debug(f"IMAP Search Criteria: {search_crit}")

    status, messages = mail.search(None, search_crit)
    log.debug(f"IMAP Search Status: {status}")

    if status != "OK":
        log.warning("No messages found or search error.")
        return []

    if not messages[0]:
        log.info("No emails found in search window.")
        return []

    return messages[0].split()


def fetch_recent_headers(mail, days=1):
    """
    Fetches only the headers of emails from the last N days.

    Headers are enough to decide whether a message was already processed, so the
    (potentially large) attachments are only downloaded for new messages. Uses
    BODY.PEEK so the \\Seen flag of the user's mailbox is left untouched.

    Returns a list of (uid, header_message_object) tuples.
    """
    log = logging.getLogger("email_ops")
    email_ids = _search_recent(mail, days)
    log.info(f"Found {len(email_ids)} emails in the search window.")

    results = []
    for eid in email_ids:
        status, msg_data = mail.fetch(eid, "(BODY.PEEK[HEADER])")
        if status != "OK":
            log.warning(f"Could not fetch headers for message {eid!r}, skipping.")
            continue
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                results.append((eid, email.message_from_bytes(response_part[1])))
                break

    return results


def fetch_message(mail, eid):
    """Fetches a full message (including attachments) by IMAP id."""
    status, msg_data = mail.fetch(eid, "(BODY.PEEK[])")
    if status != "OK":
        raise RuntimeError(f"IMAP fetch failed for message {eid!r}: {status}")
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            return email.message_from_bytes(response_part[1])
    raise RuntimeError(f"IMAP fetch returned no body for message {eid!r}")


def fetch_recent_emails(mail, days=1):
    """Fetches full emails from the last N days (kept for local/manual use)."""
    return [(eid, fetch_message(mail, eid)) for eid in _search_recent(mail, days)]


def get_email_subject(msg):
    """Returns the decoded subject, or "" for messages without one."""
    raw = msg["Subject"]
    if not raw:
        return ""
    parts = []
    for value, encoding in decode_header(raw):
        if isinstance(value, bytes):
            try:
                value = value.decode(encoding or "utf-8", errors="replace")
            except LookupError:
                value = value.decode("utf-8", errors="replace")
        parts.append(value)
    return "".join(parts)

def get_email_date(msg):
    """Returns a datetime object from email."""
    date_tuple = email.utils.parsedate_tz(msg["Date"] or "")
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
