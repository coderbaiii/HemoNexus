import math
import datetime
from backend.config import Config
from backend.database import get_db, query_db
from backend.services.verification_service import parse_iso_datetime, compute_lifecycle_status

def haversine_distance_km(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth
    in kilometers using the Haversine formula.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None
        
    R = 6371.0  # Earth's radius in kilometers
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    
    return round(R * c, 2)

def is_availability_satisfied(donor_availability, target_datetime=None):
    """
    Evaluates whether the donor's availability pattern satisfies the required request time.
    - 24_HOURS: Available at all times
    - DAYTIME: Available between 08:00 and 18:00
    - NIGHTTIME: Available between 18:00 and 08:00
    - 8_HOURS: Standard 8-hour window (09:00 - 17:00)
    Returns (satisfied: bool, suitability_score: float)
    """
    target = target_datetime or datetime.datetime.now(datetime.timezone.utc)
    hour = target.hour
    
    avail = (donor_availability or "24_HOURS").upper()
    
    if avail == "24_HOURS":
        return True, 1.0
    elif avail == "DAYTIME":
        # 08:00 to 18:00
        if 8 <= hour < 18:
            return True, 0.9
        return False, 0.0
    elif avail == "NIGHTTIME":
        # 18:00 to 08:00
        if hour >= 18 or hour < 8:
            return True, 0.9
        return False, 0.0
    elif avail == "8_HOURS":
        # 09:00 to 17:00
        if 9 <= hour < 17:
            return True, 0.85
        return False, 0.0
    else:
        # Default fallback
        return True, 0.7

def calculate_verification_recency_score(last_verified_str, now_dt=None):
    """
    Computes a freshness score (0.1 to 1.0) based on how recently the donor confirmed their profile.
    1.0 = verified today, decays linearly towards 0.1 at 180 days.
    """
    now = now_dt or datetime.datetime.now(datetime.timezone.utc)
    last_dt = parse_iso_datetime(last_verified_str)
    
    days_old = max(0.0, (now - last_dt).total_seconds() / 86400.0)
    # Linear decay over 180 days
    fraction = min(1.0, days_old / float(Config.VERIFICATION_INTERVAL_DAYS))
    score = 1.0 - (fraction * 0.9)
    return max(0.1, round(score, 3))

def find_matching_donors(blood_request_id, db=None):
    """
    Executes the 7-step requirement-based matching engine for a given blood request:
    1. Blood group must match.
    2. Donor profile must be ACTIVE.
    3. Donor availability must satisfy the required time.
    4. Donor must be within patient's preferred distance.
    5. Patient must also be within donor's maximum travel distance.
    6. Filter out unsuitable donors.
    7. Rank suitable donors using multi-criteria weighted scoring.
    """
    conn = db or get_db()
    
    # Fetch blood request
    req = query_db(
        "SELECT * FROM blood_requests WHERE id = ?",
        (blood_request_id,),
        one=True,
        db=conn
    )
    if not req:
        return []
        
    req_blood = req["required_blood_group"]
    req_dt = parse_iso_datetime(req["required_date_time"])
    req_lat = req["latitude"]
    req_lon = req["longitude"]
    pref_max_dist = float(req["preferred_max_distance"] or Config.DEFAULT_MAX_DISTANCE_KM)
    urgency = req.get("urgency", "NORMAL").upper()
    
    # Query candidate donors with user details
    # Rule 1: Blood group match
    # Rule 2: Profile status must be ACTIVE (database query filter)
    sql = """
        SELECT d.id AS donor_id, d.user_id, d.blood_group, d.phone, d.location,
               d.latitude, d.longitude, d.availability, d.maximum_travel_distance,
               d.profile_status, d.last_verified_date, d.next_verification_date,
               u.full_name, u.email
        FROM donor_profiles d
        JOIN users u ON d.user_id = u.id
        WHERE d.blood_group = ? AND d.profile_status = 'ACTIVE'
    """
    candidates = query_db(sql, (req_blood,), db=conn)
    
    # Fetch existing responses for this request to track if already contacted
    existing_responses = query_db(
        "SELECT donor_id, status, response_time, message FROM donor_request_responses WHERE blood_request_id = ?",
        (blood_request_id,),
        db=conn
    )
    contacted_map = {r["donor_id"]: r for r in existing_responses}
    
    now = datetime.datetime.now(datetime.timezone.utc)
    suitable_donors = []
    
    for donor in candidates:
        # Rule 2 check again via dynamic lifecycle status (in case date is expired but sweep hasn't run)
        next_dt = parse_iso_datetime(donor["next_verification_date"])
        live_status = compute_lifecycle_status(next_dt, current_dt=now)
        if live_status != "ACTIVE":
            continue  # Exclude non-active donor
            
        # Rule 3: Availability must satisfy the required time
        avail_ok, avail_score = is_availability_satisfied(donor["availability"], req_dt)
        if not avail_ok:
            continue  # Exclude donor whose schedule cannot fulfill request time
            
        # Distance calculation
        d_lat = donor["latitude"]
        d_lon = donor["longitude"]
        donor_max_travel = float(donor["maximum_travel_distance"] or 15.0)
        
        calculated_dist = None
        if None not in (req_lat, req_lon, d_lat, d_lon):
            calculated_dist = haversine_distance_km(req_lat, req_lon, d_lat, d_lon)
        else:
            # Fallback when coordinates are missing: sensible documented estimate based on location string match
            if req["location"] and donor["location"] and (req["location"].lower() in donor["location"].lower() or donor["location"].lower() in req["location"].lower()):
                calculated_dist = 5.0
            else:
                calculated_dist = 12.0  # Assumed metropolitan average
                
        # Rule 4: Donor must be within patient's preferred distance
        if calculated_dist > pref_max_dist:
            continue
            
        # Rule 5: Patient must also be within donor's maximum travel distance
        if calculated_dist > donor_max_travel:
            continue
            
        # Rule 6 passed! Candidate is suitable.
        
        # Rule 7: Multi-criteria ranking score calculation
        # Component A: Availability match score (0.0 to 1.0)
        s_avail = avail_score
        
        # Component B: Distance score (0.0 to 1.0, closer is higher)
        effective_max = max(pref_max_dist, donor_max_travel, 1.0)
        s_distance = max(0.0, 1.0 - (calculated_dist / effective_max))
        
        # Component C: Profile verification freshness (0.1 to 1.0)
        s_freshness = calculate_verification_recency_score(donor["last_verified_date"], now_dt=now)
        
        # Component D: Urgency modifier (if CRITICAL or URGENT, distance proximity has higher weight)
        urgency_multiplier = 1.0
        if urgency == "CRITICAL":
            urgency_multiplier = 1.2
        elif urgency == "URGENT":
            urgency_multiplier = 1.1
            
        # Composite score calculation (Presentation slide 11 formula):
        # Availability: 30%, Distance: 30%, Freshness: 20%, Proximity/Urgency fit: 20%
        raw_score = (
            (0.30 * s_avail) +
            (0.30 * s_distance * urgency_multiplier) +
            (0.20 * s_freshness) +
            (0.20 * s_distance)
        )
        
        normalized_score = round(min(100.0, raw_score * 100.0), 1)
        
        contact_info = contacted_map.get(donor["user_id"])
        
        suitable_donors.append({
            "donor_id": donor["donor_id"],
            "user_id": donor["user_id"],
            "full_name": donor["full_name"],
            "email": donor["email"],
            "blood_group": donor["blood_group"],
            "phone": donor["phone"],
            "location": donor["location"],
            "distance_km": calculated_dist,
            "maximum_travel_distance": donor_max_travel,
            "availability": donor["availability"],
            "profile_status": donor["profile_status"],
            "last_verified_date": donor["last_verified_date"],
            "next_verification_date": donor["next_verification_date"],
            "match_score": normalized_score,
            "score_breakdown": {
                "availability_score": round(s_avail * 100, 1),
                "distance_score": round(s_distance * 100, 1),
                "verification_freshness_score": round(s_freshness * 100, 1)
            },
            "contact_status": contact_info["status"] if contact_info else None,
            "is_already_contacted": contact_info is not None,
            "medical_disclaimer": "Rank score represents search priority only; medical eligibility is verified at the blood center."
        })
        
    # Sort suitable donors by match_score in descending order (highest score first)
    suitable_donors.sort(key=lambda x: x["match_score"], reverse=True)
    return suitable_donors
