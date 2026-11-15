"""
HEMONEXAS Ranking Engine
Ranks verified candidate donors according to user preference:
1. NEAREST: Ascending geographical distance
2. FASTEST: Ascending estimated travel time (clearly labeled as estimate)
3. RECENTLY_VERIFIED: Latest profile verification confirmation date
4. BEST_MATCH: Multi-factor composite matching score (availability, distance, freshness, urgency)
"""
import datetime

try:
    from backend.config import Config
except ImportError:
    from config import Config

from matching.distance import estimate_travel_time_minutes

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

def calculate_verification_recency_score(last_verified_str, now_dt=None, interval_days=180):
    """
    Computes a freshness score (0.1 to 1.0) based on how recently the donor confirmed their profile.
    1.0 = verified today, decays linearly towards 0.1 at 180 days.
    """
    now = now_dt or datetime.datetime.now(datetime.timezone.utc)
    last_dt = parse_iso_datetime(last_verified_str)
    
    days_old = max(0.0, (now - last_dt).total_seconds() / 86400.0)
    fraction = min(1.0, days_old / float(interval_days))
    score = 1.0 - (fraction * 0.9)
    return max(0.1, round(score, 3))

def calculate_matching_score(donor, patient_max_dist=25.0, urgency="NORMAL", weights=None, now_dt=None):
    """
    Calculates transparent multi-criteria composite matching_score (0.0 to 100.0).
    Factors:
    - Availability suitability (35%)
    - Geographic proximity (40%) with urgency multiplier for urgent/critical searches
    - Profile freshness / verification recency (25%)
    
    Eliminates double-counting of distance and ensures missing coordinates never receive
    a fabricated distance score.
    """
    w_avail = (weights or {}).get("weight_availability", Config.WEIGHT_AVAILABILITY)
    w_dist = (weights or {}).get("weight_distance", Config.WEIGHT_DISTANCE)
    w_fresh = (weights or {}).get("weight_freshness", Config.WEIGHT_FRESHNESS)

    # 1. Availability factor (0.0 to 1.0)
    s_avail = float(donor.get("availability_score", 0.9))

    # 2. Distance factor (0.0 to 1.0, closer is higher).
    # If distance is missing, s_dist is 0.0 (no fabricated fallback like 10.0km).
    dist = donor.get("distance_km")
    if dist is None or dist < 0:
        s_dist = 0.0
    else:
        effective_max = max(float(patient_max_dist or 25.0), float(donor.get("donor_max_travel") or 15.0), 1.0)
        s_dist = max(0.0, min(1.0, 1.0 - (float(dist) / effective_max)))

    # 3. Verification Freshness factor (0.1 to 1.0)
    s_fresh = calculate_verification_recency_score(
        donor.get("last_verified_date"),
        now_dt=now_dt,
        interval_days=Config.VERIFICATION_INTERVAL_DAYS
    )

    # 4. Urgency modifier on distance (CRITICAL=1.2, URGENT=1.1, NORMAL=1.0)
    urgency_norm = (urgency or "NORMAL").upper()
    urgency_multiplier = 1.2 if urgency_norm == "CRITICAL" else (1.1 if urgency_norm == "URGENT" else 1.0)

    # Weighted composite score without double-counting distance
    raw_score = (
        (w_avail * s_avail) +
        (w_dist * s_dist * urgency_multiplier) +
        (w_fresh * s_fresh)
    )

    normalized_score = round(min(100.0, max(0.0, raw_score * 100.0)), 1)
    
    breakdown = {
        "availability_score": round(s_avail * 100, 1),
        "distance_score": round(s_dist * 100, 1),
        "verification_freshness_score": round(s_fresh * 100, 1)
    }
    
    return normalized_score, breakdown

def rank_nearest(candidates):
    """
    Ranks candidates by distance_km ascending.
    Candidates with None distance_km sort to the end to prevent unfair competition.
    """
    ranked = sorted(
        candidates,
        key=lambda d: (d.get("distance_km") is None, d.get("distance_km") if d.get("distance_km") is not None else float("inf"))
    )
    for idx, d in enumerate(ranked, start=1):
        d["rank"] = idx
    return ranked

def rank_fastest(candidates, average_speed_kmh=30.0):
    """
    Ranks candidates by estimated_travel_time in minutes ascending.
    Clearly notes the value as estimated_travel_time.
    Candidates with None estimated_travel_time sort to the end.
    """
    speed = average_speed_kmh or Config.DEFAULT_AVERAGE_SPEED_KMH
    for d in candidates:
        dist = d.get("distance_km")
        d["estimated_travel_time"] = estimate_travel_time_minutes(dist, speed)
        
    ranked = sorted(
        candidates,
        key=lambda d: (d.get("estimated_travel_time") is None, d.get("estimated_travel_time") if d.get("estimated_travel_time") is not None else float("inf"))
    )
    for idx, d in enumerate(ranked, start=1):
        d["rank"] = idx
    return ranked

def rank_recently_verified(candidates):
    """Ranks candidates by latest last_verified_date descending."""
    ranked = sorted(
        candidates,
        key=lambda d: parse_iso_datetime(d.get("last_verified_date")),
        reverse=True
    )
    for idx, d in enumerate(ranked, start=1):
        d["rank"] = idx
    return ranked

def rank_by_donation_history(candidates):
    """Ranks candidates by total_donations count descending."""
    ranked = sorted(candidates, key=lambda d: d.get("total_donations", 0), reverse=True)
    for idx, d in enumerate(ranked, start=1):
        d["rank"] = idx
    return ranked

def rank_by_response_reliability(candidates):
    """Ranks candidates by response reliability percentage descending."""
    ranked = sorted(candidates, key=lambda d: d.get("response_reliability", 0.0), reverse=True)
    for idx, d in enumerate(ranked, start=1):
        d["rank"] = idx
    return ranked

def rank_by_compatibility(candidates, req_blood_group=None):
    """Ranks candidates by blood compatibility: exact match first, then compatible matches."""
    def comp_key(d):
        d_grp = (d.get("blood_group") or "").strip().upper()
        r_grp = (req_blood_group or "").strip().upper()
        if r_grp and d_grp == r_grp:
            return 2
        return 1
    ranked = sorted(candidates, key=comp_key, reverse=True)
    for idx, d in enumerate(ranked, start=1):
        d["rank"] = idx
    return ranked

def rank_best_match(candidates, patient_max_dist=25.0, urgency="NORMAL", weights=None, now_dt=None, req_blood_group=None):
    """
    Ranks candidates by composite matching_score descending.
    Attaches score breakdown and transparent recommendation reasons to every candidate record.
    """
    for d in candidates:
        score, breakdown = calculate_matching_score(
            d,
            patient_max_dist=patient_max_dist,
            urgency=urgency,
            weights=weights,
            now_dt=now_dt
        )
        d["matching_score"] = score
        d["score_breakdown"] = breakdown
        
        # Build transparent recommendation explanation
        reasons = []
        d_group = (d.get("blood_group") or "").strip().upper()
        r_group = (req_blood_group or d.get("required_blood_group") or "").strip().upper()
        if r_group:
            if d_group == r_group:
                reasons.append(f"Exact Blood Group Match ({d_group})")
            else:
                reasons.append(f"Medically Compatible Donor ({d_group} for {r_group})")
        else:
            reasons.append(f"Verified Blood Group {d_group}")
            
        dist = d.get("distance_km")
        if dist is not None:
            reasons.append(f"Proximity: ~{round(dist, 1)} km ({d.get('estimated_travel_time', 15)} min ETA)")
            
        if d.get("availability") == "24_HOURS":
            reasons.append("24-Hour Emergency Availability")
        elif d.get("availability"):
            reasons.append(f"Available ({d.get('availability')})")
            
        tot_donations = d.get("total_donations", 0)
        if tot_donations > 0:
            reasons.append(f"Experienced Donor ({tot_donations} donations)")
            
        rel = d.get("response_reliability")
        if rel and rel >= 80:
            reasons.append(f"High Reliability ({round(rel, 1)}% acceptance rate)")
            
        reasons.append("Active 6-Month Medical Safety Profile")
        d["recommendation_reasons"] = reasons

    ranked = sorted(candidates, key=lambda d: d.get("matching_score", 0.0), reverse=True)
    for idx, d in enumerate(ranked, start=1):
        d["rank"] = idx
    return ranked

def apply_ranking(candidates, sorting_preference="BEST_MATCH", patient_max_dist=25.0, urgency="NORMAL", average_speed_kmh=30.0, req_blood_group=None):
    """
    Applies the chosen ranking mechanism to pre-filtered valid candidates.
    Also ensures estimated_travel_time, matching_score, and transparent explanations are computed.
    """
    if not candidates:
        return []
        
    # Pre-attach travel time estimate for all candidates
    speed = average_speed_kmh or Config.DEFAULT_AVERAGE_SPEED_KMH
    for d in candidates:
        d["estimated_travel_time"] = estimate_travel_time_minutes(d.get("distance_km"), speed)
        
    pref = (sorting_preference or "BEST_MATCH").strip().upper().replace(" ", "_")

    # Always ensure matching_score & recommendation_reasons are computed for display badges
    for d in candidates:
        score, breakdown = calculate_matching_score(d, patient_max_dist=patient_max_dist, urgency=urgency)
        d["matching_score"] = score
        d["score_breakdown"] = breakdown
        if not d.get("recommendation_reasons"):
            d["recommendation_reasons"] = [
                f"Blood Group {d.get('blood_group')}",
                f"Proximity: ~{round(d.get('distance_km', 3.0), 1) if d.get('distance_km') is not None else 'Nearby'} km",
                "Active Verification Status"
            ]

    if pref in ("NEAREST", "DISTANCE", "NEAREST_DONOR"):
        return rank_nearest(candidates)

    elif pref in ("FASTEST", "TRAVEL_TIME"):
        return rank_fastest(candidates, speed)

    elif pref in ("RECENTLY_VERIFIED", "VERIFIED", "FRESH", "RECENTLY_AVAILABLE"):
        return rank_recently_verified(candidates)

    elif pref in ("DONATION_HISTORY", "HISTORY", "DONATIONS"):
        return rank_by_donation_history(candidates)

    elif pref in ("RESPONSE_RELIABILITY", "RELIABILITY"):
        return rank_by_response_reliability(candidates)

    elif pref in ("COMPATIBILITY", "BLOOD_COMPATIBILITY"):
        return rank_by_compatibility(candidates, req_blood_group)

    else:
        # Default: BEST_MATCH
        return rank_best_match(candidates, patient_max_dist=patient_max_dist, urgency=urgency, req_blood_group=req_blood_group)
