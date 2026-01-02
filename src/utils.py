import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for older python (shouldn't happen on 3.10+)
    from backports.zoneinfo import ZoneInfo
import re

# Timezone definition
CET = ZoneInfo('Europe/Prague')

def get_location_from_subject(subject):
    """
    Determines location based on email subject line.
    Original JS Logic:
      if (subject.includes("NOVA")) location = 'Nová';
      else if (subject.includes("CHECHLUVKA")) location = 'Chechlůvka';
      else if (subject.includes("TOS3")) location = 'Rákosí';
      else if (subject.includes("DUB")) location = 'Dub';  
      else location = 'Neznámá lokace';
    """
    subject_upper = subject.upper() if subject else ""
    
    if "NOVA" in subject_upper:
        return "Nová"
    elif "CHECHLUVKA" in subject_upper:
        return "Chechlůvka"
    elif "TOS3" in subject_upper:
        return "Rákosí"
    elif "DUB" in subject_upper:
        return "Dub"
    else:
        return "Neznámá lokace"

def get_service_date(dt_obj):
    """
    Calculates the 'Service Date' based on the 15:00 CET rollover rule.
    - If time < 15:00 CET: Belongs to Previous Day.
    - If time >= 15:00 CET: Belongs to Current Day.
    
    Args:
        dt_obj (datetime): The naive or aware datetime object from email.
                           If naive, assumed to be UTC or email server time 
                           (but usually email headers have offset).
    
    Returns:
        str: Date string in 'YYYY-MM-DD' format.
    """
    if dt_obj.tzinfo is None:
        # If naive, assume UTC for safety
        dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
        
    # Convert to Target Timezone (Prague)
    dt_cet = dt_obj.astimezone(CET)
    
    # Extract timestamp hour
    hour = dt_cet.hour
    
    # Logic: Day starts at 12:00 (noon). 
    
    if hour < 12:
        # Before 12:00, it belongs to the previous calendar day's logical "shift"
        service_date = dt_cet.date() - datetime.timedelta(days=1)
    else:
        # 12:00 or later, it is the start of today's logical "shift"
        service_date = dt_cet.date()
        
    return service_date.strftime("%Y-%m-%d")


def generate_filename(service_date_str, location, original_dt):
    """
    Generates filename: YYYY-MM-DD HH:MM Location.ext
    Note: Extension is handled by the saver function usually.
    """
    # User requested REAL date and time for filename.
    
    # Format: YYYY-MM-DD HH:MM {Location}
    # Note: Using spaces in filenames might be tricky for some systems, but it was requested.
    timestamp_str = original_dt.astimezone(CET).strftime("%Y-%m-%d %H:%M")
    
    return f"{timestamp_str} {location}"
