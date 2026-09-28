"""
HEMONEXAS Automated Requirement Test Suite
Covers the 20 test cases explicitly mandated in Section 24 of the specification:
 1. Correct blood group
 2. Wrong blood group
 3. Active donor
 4. Inactive donor
 5. Verification due
 6. Available donor
 7. Unavailable donor
 8. Day availability
 9. Night availability
10. Overnight availability
11. Patient distance filter
12. Donor travel limit
13. Both distance conditions
14. Nearest sorting
15. Recently verified sorting
16. Best match sorting
17. No results
18. Invalid coordinates
19. Empty database
20. Complete matching pipeline
"""
import datetime
import pytest
from matching.distance import calculate_distance_km, estimate_travel_time_minutes
from matching.availability import check_availability, is_time_in_range
from matching.filters import (
    filter_by_blood_group,
    filter_by_active_status,
    filter_by_verification_status,
    filter_by_temporary_availability,
    filter_by_availability_schedule,
    filter_by_patient_distance,
    filter_by_donor_travel_limit
)
from matching.ranking import (
    rank_nearest,
    rank_fastest,
    rank_recently_verified,
    rank_best_match,
    calculate_matching_score
)
from matching.matcher import run_matching_pipeline, MEDICAL_SAFETY_DISCLAIMER

# 1. Correct Blood Group
def test_case_1_correct_blood_group():
    donors = [
        {"id": 1, "blood_group": "B+", "name": "B Positive Donor"},
        {"id": 2, "blood_group": "A+", "name": "A Positive Donor"},
        {"id": 3, "blood_group": "B+", "name": "Another B+ Donor"}
    ]
    matched = filter_by_blood_group(donors, "B+")
    assert len(matched) == 2
    assert all(d["blood_group"] == "B+" for d in matched)

# 2. Wrong Blood Group
def test_case_2_wrong_blood_group():
    donors = [
        {"id": 1, "blood_group": "A+", "name": "Donor A"},
        {"id": 2, "blood_group": "O+", "name": "Donor O"},
        {"id": 3, "blood_group": "AB-", "name": "Donor AB-"}
    ]
    matched = filter_by_blood_group(donors, "B+")
    assert len(matched) == 0

# 3. Active Donor
def test_case_3_active_donor():
    donors = [
        {"id": 1, "profile_status": "ACTIVE"},
        {"id": 2, "profile_status": "INACTIVE"}
    ]
    matched = filter_by_active_status(donors)
    assert len(matched) == 1
    assert matched[0]["id"] == 1

# 4. Inactive Donor
def test_case_4_inactive_donor():
    donors = [
        {"id": 1, "profile_status": "INACTIVE"},
        {"id": 2, "profile_status": "INACTIVE"}
    ]
    matched = filter_by_active_status(donors)
    assert len(matched) == 0

# 5. Verification Due
def test_case_5_verification_due():
    now = datetime.datetime.now(datetime.timezone.utc)
    # Due donor (verification expired 5 days ago, within grace period)
    due_donor = {
        "id": 1,
        "profile_status": "ACTIVE",
        "next_verification_date": (now - datetime.timedelta(days=5)).isoformat()
    }
    # Current active donor (verification due in 120 days)
    active_donor = {
        "id": 2,
        "profile_status": "ACTIVE",
        "next_verification_date": (now + datetime.timedelta(days=120)).isoformat()
    }
    matched = filter_by_verification_status([due_donor, active_donor], current_dt=now)
    assert len(matched) == 1
    assert matched[0]["id"] == 2

# 6. Available Donor
def test_case_6_available_donor():
    donors = [
        {"id": 1, "is_available": 1},
        {"id": 2, "is_available": 0}
    ]
    matched = filter_by_temporary_availability(donors)
    assert len(matched) == 1
    assert matched[0]["id"] == 1

# 7. Unavailable Donor
def test_case_7_unavailable_donor():
    donors = [
        {"id": 1, "is_available": 0, "name": "Sick Donor"},
        {"id": 2, "is_available": "0", "name": "Traveling Donor"}
    ]
    matched = filter_by_temporary_availability(donors)
    assert len(matched) == 0

# 8. Day Availability (08:00 - 18:00)
def test_case_8_day_availability():
    # 12:00 -> AVAILABLE
    at_noon = datetime.datetime(2026, 9, 21, 12, 0, tzinfo=datetime.timezone.utc)
    ok_noon, score_noon, _ = check_availability("DAY", target_datetime=at_noon)
    assert ok_noon is True
    assert score_noon > 0

    # 22:00 -> NOT AVAILABLE
    at_night = datetime.datetime(2026, 9, 21, 22, 0, tzinfo=datetime.timezone.utc)
    ok_night, _, _ = check_availability("DAY", target_datetime=at_night)
    assert ok_night is False

# 9. Night Availability (18:00 - 06:00)
def test_case_9_night_availability():
    # 22:00 -> AVAILABLE
    at_22 = datetime.datetime(2026, 9, 21, 22, 0, tzinfo=datetime.timezone.utc)
    ok_22, _, _ = check_availability("NIGHT", target_datetime=at_22)
    assert ok_22 is True

    # 03:00 -> AVAILABLE
    at_03 = datetime.datetime(2026, 9, 21, 3, 0, tzinfo=datetime.timezone.utc)
    ok_03, _, _ = check_availability("NIGHT", target_datetime=at_03)
    assert ok_03 is True

    # 12:00 -> NOT AVAILABLE
    at_noon = datetime.datetime(2026, 9, 21, 12, 0, tzinfo=datetime.timezone.utc)
    ok_noon, _, _ = check_availability("NIGHT", target_datetime=at_noon)
    assert ok_noon is False

# 10. Overnight Availability (Crossing Midnight)
def test_case_10_overnight_availability():
    start = datetime.time(18, 0)
    end = datetime.time(6, 0)
    # Late night (23:30)
    assert is_time_in_range(datetime.time(23, 30), start, end) is True
    # Early morning (04:15)
    assert is_time_in_range(datetime.time(4, 15), start, end) is True
    # Midday (14:00)
    assert is_time_in_range(datetime.time(14, 0), start, end) is False

# 11. Patient Distance Filter
def test_case_11_patient_distance_filter():
    candidates = [
        {"id": 1, "distance_km": 7.0},
        {"id": 2, "distance_km": 15.0}
    ]
    # Patient allows 10 km: 7 km PASS, 15 km FAIL
    matched = filter_by_patient_distance(candidates, max_patient_distance=10.0)
    assert len(matched) == 1
    assert matched[0]["id"] == 1

# 12. Donor Travel Limit
def test_case_12_donor_travel_limit():
    candidates = [
        {"id": 1, "distance_km": 7.0, "maximum_travel_distance": 10.0},
        {"id": 2, "distance_km": 7.0, "maximum_travel_distance": 5.0} # Donor willing only 5 km
    ]
    matched = filter_by_donor_travel_limit(candidates)
    assert len(matched) == 1
    assert matched[0]["id"] == 1

# 13. Both Distance Conditions
def test_case_13_both_distance_conditions():
    # Condition: distance <= patient_max AND distance <= donor_max
    # Case A: dist 7 km, patient allows 10 km, donor allows 5 km -> REJECT
    cand_a = [{"id": 1, "distance_km": 7.0, "maximum_travel_distance": 5.0}]
    pass_patient = filter_by_patient_distance(cand_a, 10.0)
    pass_both = filter_by_donor_travel_limit(pass_patient)
    assert len(pass_both) == 0

    # Case B: dist 7 km, patient allows 10 km, donor allows 15 km -> PASS
    cand_b = [{"id": 2, "distance_km": 7.0, "maximum_travel_distance": 15.0}]
    pass_patient_b = filter_by_patient_distance(cand_b, 10.0)
    pass_both_b = filter_by_donor_travel_limit(pass_patient_b)
    assert len(pass_both_b) == 1

# 14. Nearest Sorting
def test_case_14_nearest_sorting():
    candidates = [
        {"id": 1, "distance_km": 8.0},
        {"id": 2, "distance_km": 2.5},
        {"id": 3, "distance_km": 5.1}
    ]
    ranked = rank_nearest(candidates)
    assert [d["id"] for d in ranked] == [2, 3, 1]
    assert ranked[0]["rank"] == 1

# 15. Recently Verified Sorting
def test_case_15_recently_verified_sorting():
    now = datetime.datetime.now(datetime.timezone.utc)
    candidates = [
        {"id": 1, "last_verified_date": (now - datetime.timedelta(days=90)).isoformat()},
        {"id": 2, "last_verified_date": (now - datetime.timedelta(days=2)).isoformat()},
        {"id": 3, "last_verified_date": (now - datetime.timedelta(days=30)).isoformat()}
    ]
    ranked = rank_recently_verified(candidates)
    assert [d["id"] for d in ranked] == [2, 3, 1]
    assert ranked[0]["rank"] == 1

# 16. Best Match Sorting
def test_case_16_best_match_sorting():
    now = datetime.datetime.now(datetime.timezone.utc)
    candidates = [
        # Closer, fresh verification, full 24h availability
        {"id": 1, "distance_km": 3.0, "donor_max_travel": 20.0, "availability_score": 1.0, "last_verified_date": now.isoformat()},
        # Farther, older verification
        {"id": 2, "distance_km": 18.0, "donor_max_travel": 20.0, "availability_score": 0.85, "last_verified_date": (now - datetime.timedelta(days=120)).isoformat()}
    ]
    ranked = rank_best_match(candidates, patient_max_dist=25.0, now_dt=now)
    assert ranked[0]["id"] == 1
    assert ranked[0]["matching_score"] > ranked[1]["matching_score"]

# 17. No Results
def test_case_17_no_results():
    donors = [
        {"id": 1, "blood_group": "A+", "profile_status": "ACTIVE", "is_available": 1, "latitude": 22.5, "longitude": 88.4}
    ]
    req = {
        "required_blood_group": "O-",
        "latitude": 22.5,
        "longitude": 88.4,
        "preferred_max_distance": 25.0
    }
    results = run_matching_pipeline(req, donors)
    assert len(results) == 0

# 18. Invalid Coordinates
def test_case_18_invalid_coordinates():
    # None coordinates
    assert calculate_distance_km(None, 88.4, 22.5, 88.4) is None
    # Out of range coordinates (-95 latitude)
    assert calculate_distance_km(-95.0, 88.4, 22.5, 88.4) is None
    # Non-numeric strings
    assert calculate_distance_km("invalid", "coords", 22.5, 88.4) is None

# 19. Empty Database
def test_case_19_empty_database():
    req = {
        "required_blood_group": "B+",
        "latitude": 22.5697,
        "longitude": 88.4046,
        "preferred_max_distance": 25.0
    }
    results = run_matching_pipeline(req, [])
    assert results == []

# 20. Complete Matching Pipeline
def test_case_20_complete_matching_pipeline():
    now = datetime.datetime.now(datetime.timezone.utc)
    future = (now + datetime.timedelta(days=180)).isoformat()
    
    donors = [
        # Donor 1: Perfect match (O+, Active, 24H, 3.3 km away)
        {
            "id": 1, "user_id": 101, "full_name": "Donor One",
            "blood_group": "O+", "profile_status": "ACTIVE",
            "next_verification_date": future, "last_verified_date": now.isoformat(),
            "availability": "24_HOURS", "is_available": 1,
            "latitude": 22.5805, "longitude": 88.4344, "maximum_travel_distance": 25.0
        },
        # Donor 2: Wrong blood group (A+) -> Pruned at Step 1
        {
            "id": 2, "user_id": 102, "full_name": "Donor Two",
            "blood_group": "A+", "profile_status": "ACTIVE",
            "next_verification_date": future, "last_verified_date": now.isoformat(),
            "availability": "24_HOURS", "is_available": 1,
            "latitude": 22.5805, "longitude": 88.4344, "maximum_travel_distance": 25.0
        },
        # Donor 3: Inactive donor -> Pruned at Step 2
        {
            "id": 3, "user_id": 103, "full_name": "Donor Three",
            "blood_group": "O+", "profile_status": "INACTIVE",
            "next_verification_date": (now - datetime.timedelta(days=90)).isoformat(),
            "last_verified_date": (now - datetime.timedelta(days=300)).isoformat(),
            "availability": "24_HOURS", "is_available": 1,
            "latitude": 22.5805, "longitude": 88.4344, "maximum_travel_distance": 25.0
        },
        # Donor 4: Temporarily unavailable -> Pruned at Step 4
        {
            "id": 4, "user_id": 104, "full_name": "Donor Four",
            "blood_group": "O+", "profile_status": "ACTIVE",
            "next_verification_date": future, "last_verified_date": now.isoformat(),
            "availability": "24_HOURS", "is_available": 0,
            "latitude": 22.5805, "longitude": 88.4344, "maximum_travel_distance": 25.0
        }
    ]
    
    req = {
        "required_blood_group": "O+",
        "latitude": 22.5697,
        "longitude": 88.4046,
        "preferred_max_distance": 20.0,
        "required_date_time": now.isoformat(),
        "urgency": "NORMAL",
        "sorting_preference": "BEST_MATCH"
    }
    
    results = run_matching_pipeline(req, donors, now_dt=now)
    assert len(results) == 1
    matched = results[0]
    assert matched["donor_id"] == 1
    assert matched["blood_group"] == "O+"
    assert matched["profile_status"] == "ACTIVE"
    assert matched["rank"] == 1
    assert "medical_disclaimer" in matched
    assert matched["medical_disclaimer"] == MEDICAL_SAFETY_DISCLAIMER
