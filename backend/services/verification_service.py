import datetime
from backend.config import Config
from backend.database import get_db, query_db, execute_db

def parse_iso_datetime(dt_str):
    """Safely parse an ISO format datetime string into a UTC datetime object."""
    if not dt_str:
        return None
    try:
        # Replace 'Z' with '+00:00' if present for standard parsing
        cleaned = dt_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        # Fallback to current time if unparseable
        return datetime.datetime.now(datetime.timezone.utc)

def compute_lifecycle_status(next_verification_dt, current_dt=None, interval_days=None, grace_days=None):
    """
    Computes the profile status based on the next_verification_date:
    - ACTIVE: current_dt <= next_verification_dt
    - VERIFICATION_DUE: next_verification_dt < current_dt <= next_verification_dt + grace_days
    - INACTIVE: current_dt > next_verification_dt + grace_days
    """
    now = current_dt or datetime.datetime.now(datetime.timezone.utc)
    grace = datetime.timedelta(days=grace_days or Config.GRACE_PERIOD_DAYS)
    
    if now <= next_verification_dt:
        return "ACTIVE"
    elif now <= (next_verification_dt + grace):
        return "VERIFICATION_DUE"
    else:
        return "INACTIVE"

def refresh_donor_verification(user_id, interval_days=None, db=None):
    """
    Called when a donor confirms their profile or administrator verifies them.
    Refreshes last_verified_date to NOW, next_verification_date to NOW + interval_days,
    and resets status to ACTIVE.
    """
    conn = db or get_db()
    days = interval_days or Config.VERIFICATION_INTERVAL_DAYS
    now = datetime.datetime.now(datetime.timezone.utc)
    next_due = now + datetime.timedelta(days=days)
    
    now_iso = now.isoformat()
    next_due_iso = next_due.isoformat()
    
    execute_db(
        """UPDATE donor_profiles 
           SET last_verified_date = ?, 
               next_verification_date = ?, 
               profile_status = 'ACTIVE', 
               updated_at = ?
           WHERE user_id = ?""",
        (now_iso, next_due_iso, now_iso, user_id),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, "DONOR_VERIFIED", f"Profile verified; next due date: {next_due_iso}"),
        db=conn
    )
    
    return {
        "status": "ACTIVE",
        "last_verified_date": now_iso,
        "next_verification_date": next_due_iso,
        "verification_interval_days": days
    }

def sweep_and_update_donor_statuses(db=None):
    """
    Scans all donor profiles, checks their verification dates against NOW,
    and updates any status transitions in the database.
    Does NOT delete inactive records.
    Returns summary statistics of the sweep.
    """
    conn = db or get_db()
    donors = query_db("SELECT id, user_id, profile_status, last_verified_date, next_verification_date FROM donor_profiles", db=conn)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    
    stats = {"evaluated": len(donors), "updated": 0, "active": 0, "verification_due": 0, "inactive": 0}
    
    for donor in donors:
        next_dt = parse_iso_datetime(donor["next_verification_date"])
        calculated_status = compute_lifecycle_status(next_dt, current_dt=now)
        
        if calculated_status == "ACTIVE":
            stats["active"] += 1
        elif calculated_status == "VERIFICATION_DUE":
            stats["verification_due"] += 1
        else:
            stats["inactive"] += 1
            
        if calculated_status != donor["profile_status"]:
            execute_db(
                "UPDATE donor_profiles SET profile_status = ?, updated_at = ? WHERE id = ?",
                (calculated_status, now_iso, donor["id"]),
                db=conn
            )
            execute_db(
                "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
                (donor["user_id"], "STATUS_TRANSITION", f"Status changed from {donor['profile_status']} to {calculated_status}"),
                db=conn
            )
            stats["updated"] += 1
            
    return stats

def get_donor_verification_details(user_id, db=None):
    """
    Returns full verification telemetry for a donor user.
    """
    conn = db or get_db()
    donor = query_db(
        "SELECT id, user_id, profile_status, last_verified_date, next_verification_date, updated_at FROM donor_profiles WHERE user_id = ?",
        (user_id,),
        one=True,
        db=conn
    )
    if not donor:
        return None
        
    now = datetime.datetime.now(datetime.timezone.utc)
    next_dt = parse_iso_datetime(donor["next_verification_date"])
    grace = datetime.timedelta(days=Config.GRACE_PERIOD_DAYS)
    
    current_status = compute_lifecycle_status(next_dt, current_dt=now)
    days_until_due = (next_dt - now).total_seconds() / 86400.0
    days_until_inactive = ((next_dt + grace) - now).total_seconds() / 86400.0
    
    return {
        "profile_status": current_status,
        "last_verified_date": donor["last_verified_date"],
        "next_verification_date": donor["next_verification_date"],
        "days_until_due": round(days_until_due, 1),
        "days_until_inactive": round(max(0, days_until_inactive), 1),
        "grace_period_days": Config.GRACE_PERIOD_DAYS,
        "verification_interval_days": Config.VERIFICATION_INTERVAL_DAYS,
        "is_action_required": current_status in ("VERIFICATION_DUE", "INACTIVE")
    }
