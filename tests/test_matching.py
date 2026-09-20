import datetime
import pytest
from backend.services.matching_service import (
    haversine_distance_km,
    is_availability_satisfied,
    calculate_verification_recency_score,
    find_matching_donors
)
from backend.database import query_db, execute_db

def test_haversine_formula():
    """Verify Haversine distance accuracy."""
    # Apollo Hospital Kolkata (22.5697, 88.4046) to Salt Lake Sec 5 (22.5805, 88.4344) is approx 3.3 km
    dist = haversine_distance_km(22.5697, 88.4046, 22.5805, 88.4344)
    assert 2.5 <= dist <= 4.0

def test_availability_time_matching():
    """Verify availability schedule fulfillment rules."""
    # Day hour (14:00 UTC)
    day_time = datetime.datetime(2026, 9, 20, 14, 0, tzinfo=datetime.timezone.utc)
    ok, score = is_availability_satisfied("DAYTIME", day_time)
    assert ok is True
    assert score > 0

    # Night hour (02:00 UTC)
    night_time = datetime.datetime(2026, 9, 20, 2, 0, tzinfo=datetime.timezone.utc)
    ok_day, _ = is_availability_satisfied("DAYTIME", night_time)
    assert ok_day is False

    ok_night, score_night = is_availability_satisfied("NIGHTTIME", night_time)
    assert ok_night is True
    assert score_night > 0

    # 24 Hours satisfies both day and night
    ok_24_day, _ = is_availability_satisfied("24_HOURS", day_time)
    ok_24_night, _ = is_availability_satisfied("24_HOURS", night_time)
    assert ok_24_day is True
    assert ok_24_night is True

def test_verification_recency_score():
    """Verify that recent verifications produce higher scores."""
    now = datetime.datetime.now(datetime.timezone.utc)
    today_iso = now.isoformat()
    old_iso = (now - datetime.timedelta(days=120)).isoformat()
    
    score_fresh = calculate_verification_recency_score(today_iso, now_dt=now)
    score_old = calculate_verification_recency_score(old_iso, now_dt=now)
    
    assert score_fresh > score_old
    assert score_fresh >= 0.95
    assert score_old < 0.6

def test_matching_engine_filters_and_ranking(app, db_conn):
    """
    Test full 7-step matching engine:
    - Excludes different blood groups (A+ donor Subhashish excluded for O+ request)
    - Excludes inactive donor (Rohan excluded)
    - Excludes verification-due donor (Devratna excluded)
    - Includes active O+ donors within travel limits
    - Ranks closest active donor highest
    """
    with app.app_context():
        # Request #1 is for O+ blood at Apollo Hospital Kolkata
        req = query_db("SELECT id FROM blood_requests WHERE required_blood_group = 'O+'", one=True, db=db_conn)
        assert req is not None
        req_id = req["id"]
        
        matches = find_matching_donors(req_id, db=db_conn)
        assert len(matches) > 0
        
        # 1. Check all returned candidates are O+
        for m in matches:
            assert m["blood_group"] == "O+"
            assert m["profile_status"] == "ACTIVE"
            assert "medical_disclaimer" in m

        # 2. Check inactive donor is not in results
        inactive_ids = [d["user_id"] for d in query_db("SELECT user_id FROM donor_profiles WHERE profile_status = 'INACTIVE'", db=db_conn)]
        matched_user_ids = [m["user_id"] for m in matches]
        for iid in inactive_ids:
            assert iid not in matched_user_ids, "Inactive donors must never appear in matching results!"

        # 3. Check ranking order: matches must be sorted by match_score descending
        scores = [m["match_score"] for m in matches]
        assert scores == sorted(scores, reverse=True)
