import datetime
import pytz
import re

# Timezone definition
CET = pytz.timezone('Europe/Prague')

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
        # If naive, assume UTC for safety, though email parsing usually handles this.
        dt_obj = pytz.utc.localize(dt_obj)
        
    # Convert to Target Timezone (Prague)
    dt_cet = dt_obj.astimezone(CET)
    
    # Extract timestamp hour
    hour = dt_cet.hour
    
    # Logic: Day starts at 15:00. 
    # Example: 19th 14:00 -> Belongs to 18th (Wait, "Day starts at 15:00")
    # Clarification from user: "day starts at 15:00 CET and ends 14:59 CET"
    # So: 
    # 2023-12-19 14:59 -> Part of 18th's shift? 
    # 2023-12-19 15:00 -> Start of 19th's shift?
    # Usually "Service Day X" covers 15:00 Day X to 14:59 Day X+1? 
    # OR "Service Day X" covers 15:00 Day X-1 to 14:59 Day X?
    
    # Let's assume standard logic: 
    # If today is 19th 16:00, that is "Day 19".
    # If today is 19th 10:00, that is "Day 18" (night shift).
    
    if hour < 15:
        # Before 15:00, it belongs to the previous calendar day's logical "shift"
        service_date = dt_cet.date() - datetime.timedelta(days=1)
    else:
        # 15:00 or later, it is the start of today's logical "shift"
        service_date = dt_cet.date()
        
    return service_date.strftime("%Y-%m-%d")

def generate_filename(service_date_str, location, original_dt):
    """
    Generates filename: YYYY-MM-DD_Location_HH-MM-SS.ext
    Note: Extension is handled by the saver function usually, 
    but we return the Base name here.
    """
    # Safe location string (remove spaces, special chars for filesystem safety/Drive safety)
    # User asked for: "YYYY-MM-DD and then location"
    # I added timestamp to prevent overwrites.
    
    # Normalize location for filename (Optional but good practice)
    # keeping it simple: 'Nová' -> 'Nova' might be safer but user used accents in JS.
    # Python 3 handles utf-8 fine.
    
    # Format time for uniqueness
    time_str = original_dt.astimezone(CET).strftime("%H-%M-%S")
    
    return f"{service_date_str}_{location}_{time_str}"
