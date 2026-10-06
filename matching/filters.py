"""
HEMONEXAS Modular Filtering Pipeline
Each filter function operates on candidate donors with single-responsibility logic.
Adheres strictly to the principle:
Filtering answers: "Should this donor appear at all?"
Ranking answers: "Among suitable donors, which should appear first?"
Invalid candidates are pruned and cannot be resurrected by ranking.
"""
import datetime
import logging

try:
    from backend.config import Config
except ImportError:
    from config import Config

from matching.distance import calculate_distance_km
from matching.availability import check_availability

logger = logging.getLogger(__name__)

def parse_iso_datetime(dt_str):
    """Safely parse ISO datetime string into UTC datetime object."""
    if not dt_str:
        return None
    try:
        cleaned = dt_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return datetime.datetime.now(datetime.timezone.utc)

def compute_lifecycle_status(next_verification_dt, current_dt=None, grace_days=30):
    """
    Computes profile verification lifecycle status:
    - ACTIVE: current_dt <= next_verification_dt
    - VERIFICATION_DUE: next_verification_dt < current_dt <= next_verification_dt + grace_days
    - INACTIVE: current_dt > next_verification_dt + grace_days
    - UNKNOWN: next_verification_dt is None or invalid
    """
    if next_verification_dt is None:
        return "UNKNOWN"
        
    now = current_dt or datetime.datetime.now(datetime.timezone.utc)
    grace = datetime.timedelta(days=grace_days)
    
    if now <= next_verification_dt:
        return "ACTIVE"
    elif now <= (next_verification_dt + grace):
        return "VERIFICATION_DUE"
    else:
        return "INACTIVE"

def filter_by_blood_group(candidates, required_blood_group):
    """
    Filters donors by requested blood group.
    MVP uses strict exact blood group matching for discovery.
    Designed modularly to integrate authorized blood bank compatibility matrices in future.
    """
    if not required_blood_group:
        return []
    req_group = required_blood_group.strip().upper()
    return [d for d in candidates if (d.get("blood_group") or "").strip().upper() == req_group]

def filter_by_active_status(candidates):
    """Filters out any donor whose database profile_status is not 'ACTIVE'."""
    return [d for d in candidates if (d.get("profile_status") or "").strip().upper() == "ACTIVE"]

def filter_by_verification_status(candidates, current_dt=None, grace_days=None):
    """
    Ensures donor's next_verification_date has not lapsed into VERIFICATION_DUE, INACTIVE, or UNKNOWN.
    Does not allow unverified or expired donors to match in emergency searches.
    Uses runtime DB setting for grace_days if not explicitly provided.
    """
    # Read runtime interval and grace from DB if not provided
    try:
        from backend.app import get_system_setting, get_db as _get_db
        conn = _get_db()
        i_val = get_system_setting("verification_interval_seconds", db=conn)
        interval_days = float(i_val) / 86400.0 if i_val is not None else Config.VERIFICATION_INTERVAL_DAYS
        if grace_days is None:
            g_val = get_system_setting("grace_period_seconds", db=conn)
            grace_days = float(g_val) / 86400.0 if g_val is not None else Config.GRACE_PERIOD_DAYS
    except Exception:
        interval_days = Config.VERIFICATION_INTERVAL_DAYS
        grace_days = grace_days if grace_days is not None else Config.GRACE_PERIOD_DAYS

    now = current_dt or datetime.datetime.now(datetime.timezone.utc)
    valid = []
    for d in candidates:
        donor_id = d.get("donor_id") or d.get("id") or d.get("user_id")
        last_due_str = d.get("last_verified_date") or d.get("next_verification_date")

        if not last_due_str:
            logger.warning(
                "Donor %s excluded from matching: verification timestamp is missing.",
                donor_id
            )
            continue

        last_dt = parse_iso_datetime(last_due_str)
        if not last_dt:
            logger.warning(
                "Donor %s excluded from matching: invalid verification timestamp '%s'.",
                donor_id, last_due_str
            )
            continue

        # Dynamic expiration = last_verified_date + interval
        next_dt = last_dt + datetime.timedelta(days=interval_days)

        status = compute_lifecycle_status(next_dt, current_dt=now, grace_days=grace_days)
        if status == "ACTIVE":
            valid.append(d)
        else:
            logger.info(
                "Donor %s excluded from matching: verification status is %s.",
                donor_id, status
            )
    return valid

def filter_by_donation_cooldown(candidates, current_dt=None, cooldown_days=None):
    """
    Filters out donors who have donated within the operational donation cooldown period.
    
    IMPORTANT MEDICAL DISCLAIMER:
    This software filter enforces an operational search cooldown window (default 56 days)
    for scheduling prioritization and donor rest intervals. It does NOT determine medical
    eligibility. Final donor deferral, infectious disease screening, and clinical release
    are determined strictly by authorized blood centre medical officers in accordance
    with applicable health authority guidelines.
    
    Parameters:
      candidates: list of donor dicts, potentially containing 'last_donation_date'
      current_dt: reference UTC datetime (defaults to now)
      cooldown_days: int/float days (defaults to Config.DEFAULT_DONATION_COOLDOWN_DAYS)
      
    Returns:
      list of candidates eligible under the operational cooldown policy.
    """
    if cooldown_days is None:
        cooldown_days = getattr(Config, "DEFAULT_DONATION_COOLDOWN_DAYS", 56)
        
    try:
        cooldown_days = float(cooldown_days)
    except (ValueError, TypeError):
        cooldown_days = 56.0
        
    if cooldown_days <= 0:
        return list(candidates)
        
    now = current_dt or datetime.datetime.now(datetime.timezone.utc)
    valid = []
    for d in candidates:
        last_donation_str = d.get("last_donation_date")
        if not last_donation_str:
            # No prior donation recorded -> candidate passes operational cooldown
            valid.append(d)
            continue
            
        last_dt = parse_iso_datetime(last_donation_str)
        if not last_dt:
            valid.append(d)
            continue
            
        days_since = (now - last_dt).total_seconds() / 86400.0
        if days_since >= cooldown_days:
            valid.append(d)
        else:
            donor_id = d.get("donor_id") or d.get("id") or d.get("user_id")
            logger.info(
                "Donor %s excluded from matching: in donation cooldown (%.1f days since donation < %.1f days threshold).",
                donor_id, days_since, cooldown_days
            )
            d_copy = dict(d)
            d_copy["cooldown_excluded"] = True
            d_copy["exclusion_reason"] = f"In operational donation cooldown ({days_since:.1f} days < {cooldown_days:.0f} days)"
    return valid

def filter_by_temporary_availability(candidates):
    """Filters out donors who have toggled themselves temporarily unavailable."""
    return [d for d in candidates if d.get("is_available", 1) not in (0, False, "0", "false")]

def filter_by_availability_schedule(candidates, target_datetime=None):
    """
    Filters donors whose schedule pattern does not cover the requested time.
    Attaches availability_score and status_label to the candidate record.
    """
    now = target_datetime or datetime.datetime.now(datetime.timezone.utc)
    valid = []
    for d in candidates:
        avail_type = d.get("availability") or "24_HOURS"
        is_avail = d.get("is_available", 1)
        avail_from = d.get("available_from")
        avail_to = d.get("available_to")
        
        ok, score, label = check_availability(
            availability_type=avail_type,
            target_datetime=now,
            is_available=is_avail,
            available_from=avail_from,
            available_to=avail_to
        )
        if ok:
            candidate_copy = dict(d)
            candidate_copy["availability_score"] = score
            candidate_copy["availability_label"] = label
            valid.append(candidate_copy)
    return valid

def calculate_and_attach_distances(candidates, patient_lat, patient_lon):
    """
    Calculates Haversine distance for all candidates and attaches distance_km.
    If coordinates are missing or invalid, distance_km is set to None.
    NEVER substitutes a fabricated distance (such as 12.0 km).
    """
    enriched = []
    for d in candidates:
        d_lat = d.get("latitude")
        d_lon = d.get("longitude")
        dist = calculate_distance_km(d_lat, d_lon, patient_lat, patient_lon)
        
        candidate_copy = dict(d)
        candidate_copy["distance_km"] = dist
        enriched.append(candidate_copy)
    return enriched

def filter_by_patient_distance(candidates, max_patient_distance):
    """
    Filters donors outside the patient's maximum acceptable search radius.
    Condition: actual_distance <= patient_max_distance
    Donors with unavailable coordinates (distance_km is None) are excluded
    as spatial proximity cannot be established.
    """
    if max_patient_distance is None:
        max_dist = 25.0
    else:
        try:
            max_dist = float(max_patient_distance)
        except (ValueError, TypeError):
            max_dist = 25.0
            
    return [d for d in candidates if d.get("distance_km") is not None and d.get("distance_km") <= max_dist]

def filter_by_donor_travel_limit(candidates):
    """
    Filters donors who are unwilling to travel the calculated distance.
    Condition: actual_distance <= donor_maximum_travel_distance
    """
    valid = []
    for d in candidates:
        dist = d.get("distance_km")
        if dist is None:
            continue
        try:
            max_travel = float(d.get("maximum_travel_distance") or 15.0)
        except (ValueError, TypeError):
            max_travel = 15.0
            
        if dist <= max_travel:
            candidate_copy = dict(d)
            candidate_copy["donor_max_travel"] = max_travel
            valid.append(candidate_copy)
    return valid
