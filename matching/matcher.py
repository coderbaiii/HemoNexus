"""
HEMONEXAS Matching Pipeline Orchestrator
Connects individual filters, distance calculations, and ranking algorithms
into a unified, transparent execution pipeline.

Pipeline:
PATIENT REQUEST
        ↓
1. Blood Group Filter
        ↓
2. Active Profile Check
        ↓
3. Verification Check (6-Month Lifecycle)
        ↓
4. Temporary Availability Check
        ↓
5. Availability Schedule Check
        ↓
6. Haversine Distance Calculation
        ↓
7. Patient Distance Filter
        ↓
8. Donor Maximum Travel Limit Check
        ↓
Candidate List (Pruned & Validated)
        ↓
9. Multi-Criteria Ranking / Sorting (Nearest, Fastest, Verified, Best Match)
        ↓
Final Results with Privacy Safeguards & Medical Safety Disclaimers
"""
import datetime

try:
    from backend.config import Config
except ImportError:
    from config import Config

try:
    from backend.database import get_db, query_db
except ImportError:
    from database.db import get_db, query_db

from matching.filters import (
    filter_by_blood_group,
    filter_by_active_status,
    filter_by_verification_status,
    filter_by_donation_cooldown,
    filter_by_temporary_availability,
    filter_by_availability_schedule,
    calculate_and_attach_distances,
    filter_by_patient_distance,
    filter_by_donor_travel_limit,
    parse_iso_datetime
)
from matching.ranking import apply_ranking

MEDICAL_SAFETY_DISCLAIMER = (
    "Operational search priority only. All final medical donor screenings, infectious disease "
    "evaluations, cross-matching, and blood release are performed strictly by authorized blood bank medical staff."
)

def run_matching_pipeline(request_data, candidate_donors, sorting_preference=None, now_dt=None):
    """
    Executes the complete filtering and ranking pipeline given a request dict
    and raw candidate donor list.
    
    Parameters:
      request_data: dict with keys:
        - required_blood_group (str)
        - latitude (float)
        - longitude (float)
        - preferred_max_distance (float)
        - required_date_time (iso str)
        - urgency (str)
        - sorting_preference (str)
        - donation_cooldown_days (int/float, optional override)
      candidate_donors: list of donor dicts
      sorting_preference: optional override of sorting method
      now_dt: optional datetime.datetime override for testing
      
    Returns:
      list of ranked donor result dictionaries
    """
    now = now_dt or datetime.datetime.now(datetime.timezone.utc)
    
    req_blood = request_data.get("required_blood_group")
    req_lat = request_data.get("latitude")
    req_lon = request_data.get("longitude")
    max_patient_dist = float(request_data.get("preferred_max_distance") or Config.DEFAULT_MAX_DISTANCE_KM)
    req_dt = parse_iso_datetime(request_data.get("required_date_time")) or now
    urgency = request_data.get("urgency", "NORMAL")
    sort_pref = sorting_preference or request_data.get("sorting_preference", "BEST_MATCH")
    cooldown_days = request_data.get("donation_cooldown_days")

    # Step 1: Blood Group Filter
    step1 = filter_by_blood_group(candidate_donors, req_blood)
    if not step1:
        return []

    # Step 2: Active Profile Check (Database status == 'ACTIVE')
    step2 = filter_by_active_status(step1)
    if not step2:
        return []

    # Step 3: Verification Check (Dynamic 6-month verification check against now)
    step3 = filter_by_verification_status(step2, current_dt=now, grace_days=Config.GRACE_PERIOD_DAYS)
    if not step3:
        return []

    # Step 3b: Operational Donation Cooldown Check
    step3b = filter_by_donation_cooldown(step3, current_dt=now, cooldown_days=cooldown_days)
    if not step3b:
        return []

    # Step 4: Temporary Availability Check (is_available != 0)
    step4 = filter_by_temporary_availability(step3b)
    if not step4:
        return []

    # Step 5: Availability Schedule Check (24H, 8H, DAY, NIGHT covering req_dt)
    step5 = filter_by_availability_schedule(step4, target_datetime=req_dt)
    if not step5:
        return []

    # Step 6: Distance Calculation (Haversine formula in km)
    step6 = calculate_and_attach_distances(step5, req_lat, req_lon)

    # Step 7: Patient Distance Filter (distance <= patient search radius)
    step7 = filter_by_patient_distance(step6, max_patient_dist)
    if not step7:
        return []

    # Step 8: Donor Maximum Travel Distance Check (distance <= donor travel limit)
    candidate_list = filter_by_donor_travel_limit(step7)
    if not candidate_list:
        return []

    # Step 9: Ranking / Sorting (Nearest, Fastest, Recently Verified, or Best Match)
    ranked_candidates = apply_ranking(
        candidate_list,
        sorting_preference=sort_pref,
        patient_max_dist=max_patient_dist,
        urgency=urgency,
        average_speed_kmh=Config.DEFAULT_AVERAGE_SPEED_KMH
    )

    # Step 10: Final Results Preparation & Privacy Safeguards
    # Exact coordinates and street address are masked; contact reveals follow consent workflow
    final_results = []
    for d in ranked_candidates:
        sanitized = {
            "rank": d.get("rank"),
            "donor_id": d.get("donor_id") or d.get("id"),
            "user_id": d.get("user_id"),
            "full_name": d.get("full_name", "Anonymous Donor"),
            "blood_group": d.get("blood_group"),
            "approximate_distance_km": d.get("distance_km"),
            "distance_km": d.get("distance_km"),  # For backward-compatible tests
            "estimated_travel_time": d.get("estimated_travel_time"),
            "availability": d.get("availability"),
            "availability_label": d.get("availability_label"),
            "maximum_travel_distance": d.get("donor_max_travel", d.get("maximum_travel_distance")),
            "profile_status": d.get("profile_status"),
            "last_verified_date": d.get("last_verified_date"),
            "next_verification_date": d.get("next_verification_date"),
            "match_score": d.get("matching_score"),
            "matching_score": d.get("matching_score"),
            "score_breakdown": d.get("score_breakdown"),
            "masked_location": d.get("location", "Kolkata Region"),
            "phone": d.get("phone"),
            "email": d.get("email"),
            "contact_status": d.get("contact_status"),
            "is_already_contacted": d.get("is_already_contacted", False),
            "medical_disclaimer": MEDICAL_SAFETY_DISCLAIMER
        }
        final_results.append(sanitized)

    return final_results

def find_matching_donors(blood_request_id, db=None, override_sort=None):
    """
    Loads blood request from database, retrieves all candidate donors,
    and runs the full 10-step matching pipeline.
    """
    conn = db or get_db()
    
    # 1. Fetch Blood Request
    req = query_db("SELECT * FROM blood_requests WHERE id = ?", (blood_request_id,), one=True, db=conn)
    if not req:
        return []

    # 2. Fetch candidate donors with user accounts
    sql = """
        SELECT d.id AS donor_id, d.user_id, d.blood_group, d.phone, d.location,
               d.latitude, d.longitude, d.availability, d.available_from, d.available_to,
               d.maximum_travel_distance, d.profile_status,
               CASE WHEN d.profile_status = 'TEMPORARILY_UNAVAILABLE' THEN 0 ELSE 1 END AS is_available,
               d.last_verified_date, d.next_verification_date,
               (SELECT MAX(donation_date) FROM donation_records WHERE donor_id = d.user_id) AS last_donation_date,
               u.full_name, u.email
        FROM donor_profiles d
        JOIN users u ON d.user_id = u.id
    """
    raw_donors = query_db(sql, db=conn)
    
    # Check existing contact responses
    existing_responses = query_db(
        "SELECT donor_id, status, response_time, message FROM donor_request_responses WHERE blood_request_id = ?",
        (blood_request_id,),
        db=conn
    )
    contacted_map = {r["donor_id"]: r for r in (existing_responses or [])}
    
    for d in raw_donors:
        contact_info = contacted_map.get(d["user_id"])
        if contact_info:
            d["contact_status"] = contact_info["status"]
            d["is_already_contacted"] = True
        else:
            d["contact_status"] = None
            d["is_already_contacted"] = False

    sort_pref = override_sort or req.get("sorting_preference") or req.get("sort_preference", "BEST_MATCH")
    return run_matching_pipeline(req, raw_donors, sorting_preference=sort_pref)
