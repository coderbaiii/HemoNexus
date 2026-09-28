"""
HEMONEXAS Availability Engine
Handles donor schedule matching, time-window verification,
and robust overnight crossing-midnight interval calculations.
"""
import datetime

def parse_time_str(time_str):
    """
    Parses 'HH:MM' string into a datetime.time object.
    Returns datetime.time or None.
    """
    if not time_str:
        return None
    try:
        parts = time_str.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return datetime.time(hour=hour, minute=minute)
    except Exception:
        return None

def is_time_in_range(current_time, start_time, end_time):
    """
    Determines if current_time falls between start_time and end_time.
    
    CRITICAL: Correctly handles intervals that cross midnight!
    - Normal daytime (e.g. 08:00 to 18:00):
      start <= current < end
    - Overnight crossing midnight (e.g. 18:00 to 06:00):
      current >= start OR current < end
    """
    if start_time == end_time:
        # Full 24-hour coverage
        return True
        
    if start_time < end_time:
        # Standard daytime range (e.g. 08:00 to 18:00)
        return start_time <= current_time < end_time
    else:
        # Overnight range crossing midnight (e.g. 18:00 to 06:00)
        return current_time >= start_time or current_time < end_time

def check_availability(availability_type, target_datetime=None, is_available=1, available_from=None, available_to=None):
    """
    Evaluates whether the donor is available for a blood request at target_datetime.
    
    Supported types:
    - '24_HOURS' / '24 HOURS': Always available (suitability 1.0)
    - 'DAY' / 'DAYTIME': 08:00 to 18:00 (suitability 0.9)
    - 'NIGHT' / 'NIGHTTIME': 18:00 to 06:00 (crosses midnight, suitability 0.9)
    - '8_HOURS' / '8 HOURS': 09:00 to 17:00 (suitability 0.85)
    - Custom range: uses available_from and available_to if specified
    
    Parameters:
      availability_type: str
      target_datetime: datetime.datetime (defaults to current UTC time)
      is_available: int/bool (temporary availability toggle: 0 = False, 1 = True)
      available_from: str 'HH:MM' (optional custom window)
      available_to: str 'HH:MM' (optional custom window)
      
    Returns:
      (is_available: bool, suitability_score: float, status_label: str)
    """
    # 1. Temporary unavailability check
    if is_available in (0, False, "0", "false"):
        return False, 0.0, "Temporarily Unavailable"

    target_dt = target_datetime or datetime.datetime.now(datetime.timezone.utc)
    current_time = target_dt.time()
    
    avail_norm = (availability_type or "24_HOURS").strip().upper().replace(" ", "_")

    # 2. Check predefined patterns
    if avail_norm in ("24_HOURS", "24_HOUR", "ALL_DAY"):
        return True, 1.0, "Available (24 Hours)"

    elif avail_norm in ("DAY", "DAYTIME"):
        start = datetime.time(8, 0)
        end = datetime.time(18, 0)
        in_range = is_time_in_range(current_time, start, end)
        score = 0.9 if in_range else 0.0
        label = "Available (Daytime 08:00-18:00)" if in_range else "Unavailable (Outside Daytime Window)"
        return in_range, score, label

    elif avail_norm in ("NIGHT", "NIGHTTIME"):
        start = datetime.time(18, 0)
        end = datetime.time(6, 0)  # Overnight crossing midnight
        in_range = is_time_in_range(current_time, start, end)
        score = 0.9 if in_range else 0.0
        label = "Available (Nighttime 18:00-06:00)" if in_range else "Unavailable (Outside Nighttime Window)"
        return in_range, score, label

    elif avail_norm in ("8_HOURS", "8_HOUR", "STANDARD_SHIFT"):
        start = datetime.time(9, 0)
        end = datetime.time(17, 0)
        in_range = is_time_in_range(current_time, start, end)
        score = 0.85 if in_range else 0.0
        label = "Available (8-Hour Shift 09:00-17:00)" if in_range else "Unavailable (Outside 8-Hour Shift)"
        return in_range, score, label

    else:
        # Custom time range if valid strings provided
        custom_start = parse_time_str(available_from)
        custom_end = parse_time_str(available_to)
        if custom_start and custom_end:
            in_range = is_time_in_range(current_time, custom_start, custom_end)
            score = 0.85 if in_range else 0.0
            label = f"Available ({available_from}-{available_to})" if in_range else "Unavailable (Outside Custom Window)"
            return in_range, score, label
            
        # Default fallback
        return True, 0.7, "Available (General)"
