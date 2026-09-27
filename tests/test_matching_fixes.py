"""
HEMONEXAS Unit and Integration Tests for Member 3 Priorities:
- Priority 1: Missing coordinate handling (no fabricated 12.0km or 10.0km fallback).
- Priority 2: Configurable donation cooldown based on last donation date (with medical disclaimers).
- Priority 3: Explicit handling of missing next_verification_date (UNKNOWN state, logged).
- Priority 4: Six-month verification workflow with configurable grace period (ACTIVE -> VERIFICATION_DUE -> INACTIVE).
- Priority 5: Inspection and fix of calculate_matching_score to eliminate double-counting of distance.
"""
import datetime
import pytest
from config import Config
from matching.filters import (
    calculate_and_attach_distances,
    filter_by_patient_distance,
    filter_by_donation_cooldown,
    filter_by_verification_status,
    compute_lifecycle_status
)
from matching.ranking import (
    calculate_matching_score,
    rank_nearest,
    rank_fastest
)
from matching.matcher import run_matching_pipeline

# -------------------------------------------------------------
# PRIORITY 1: Missing Coordinate Handling
# -------------------------------------------------------------

def test_missing_coordinates_receives_none_not_fabricated_12km():
    """Verify that calculate_and_attach_distances never assigns fabricated 12.0km."""
    candidates = [
        {"id": 1, "latitude": None, "longitude": None},
        {"id": 2, "latitude": 22.5805, "longitude": 88.4344},
        {"id": 3, "latitude": "invalid", "longitude": 88.4046}
    ]
    enriched = calculate_and_attach_distances(candidates, patient_lat=22.5697, patient_lon=88.4046)
    
    # Candidate 1: Missing coordinates -> distance_km must be None
    assert enriched[0]["distance_km"] is None
    # Candidate 2: Valid coordinates -> distance_km must be computed float (~3.29 km)
    assert enriched[1]["distance_km"] is not None
    assert 2.5 <= enriched[1]["distance_km"] <= 4.0
    # Candidate 3: Invalid string coordinates -> distance_km must be None
    assert enriched[2]["distance_km"] is None

def test_missing_coordinates_excluded_by_patient_distance_filter():
    """Verify that donors with None distance_km are safely excluded from spatial search radius."""
    candidates = [
        {"id": 1, "distance_km": None},
        {"id": 2, "distance_km": 15.0},
        {"id": 3, "distance_km": 30.0}
    ]
    # Max radius = 20.0 km
    passed = filter_by_patient_distance(candidates, max_patient_distance=20.0)
    assert len(passed) == 1
    assert passed[0]["id"] == 2

def test_missing_coordinates_score_calculation_does_not_use_fake_10km():
    """Verify calculate_matching_score assigns distance_score=0.0 when distance_km is None."""
    donor_with_none = {
        "id": 1,
        "distance_km": None,
        "availability_score": 1.0,
        "last_verified_date": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    score, breakdown = calculate_matching_score(donor_with_none, patient_max_dist=25.0)
    assert breakdown["distance_score"] == 0.0

def test_missing_coordinates_sort_last_in_nearest_ranking():
    """Verify candidates with None distance_km sort to the end and never outrank valid donors."""
    candidates = [
        {"id": 1, "distance_km": None},
        {"id": 2, "distance_km": 12.0},
        {"id": 3, "distance_km": 2.5}
    ]
    ranked = rank_nearest(candidates)
    assert [d["id"] for d in ranked] == [3, 2, 1]
    assert ranked[0]["id"] == 3
    assert ranked[2]["id"] == 1


# -------------------------------------------------------------
# PRIORITY 2: Configurable Donation Cooldown
# -------------------------------------------------------------

def test_donation_cooldown_filters_recent_donation():
    """Donors who donated 20 days ago are excluded under default 56-day cooldown."""
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_date = (now - datetime.timedelta(days=20)).isoformat()
    candidates = [
        {"id": 1, "last_donation_date": recent_date}
    ]
    valid = filter_by_donation_cooldown(candidates, current_dt=now, cooldown_days=56)
    assert len(valid) == 0

def test_donation_cooldown_allows_past_cooldown_donation():
    """Donors who donated 60 days ago are eligible under default 56-day cooldown."""
    now = datetime.datetime.now(datetime.timezone.utc)
    old_donation_date = (now - datetime.timedelta(days=60)).isoformat()
    candidates = [
        {"id": 1, "last_donation_date": old_donation_date}
    ]
    valid = filter_by_donation_cooldown(candidates, current_dt=now, cooldown_days=56)
    assert len(valid) == 1
    assert valid[0]["id"] == 1

def test_donation_cooldown_allows_first_time_donor():
    """Donors without a prior donation history (last_donation_date is None) pass cooldown."""
    now = datetime.datetime.now(datetime.timezone.utc)
    candidates = [
        {"id": 1, "last_donation_date": None},
        {"id": 2}
    ]
    valid = filter_by_donation_cooldown(candidates, current_dt=now, cooldown_days=56)
    assert len(valid) == 2

def test_donation_cooldown_configurable_override():
    """Verify custom cooldown intervals (e.g. 90 days vs 15 days vs 0 days)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    donation_30d_ago = (now - datetime.timedelta(days=30)).isoformat()
    candidates = [{"id": 1, "last_donation_date": donation_30d_ago}]
    
    # 90-day cooldown: 30 days is within cooldown -> excluded
    assert len(filter_by_donation_cooldown(candidates, current_dt=now, cooldown_days=90)) == 0
    # 15-day cooldown: 30 days is beyond cooldown -> eligible
    assert len(filter_by_donation_cooldown(candidates, current_dt=now, cooldown_days=15)) == 1
    # 0-day cooldown (disabled): eligible
    assert len(filter_by_donation_cooldown(candidates, current_dt=now, cooldown_days=0)) == 1

def test_pipeline_integrates_donation_cooldown():
    """Verify run_matching_pipeline excludes donors currently in cooldown."""
    now = datetime.datetime.now(datetime.timezone.utc)
    future = (now + datetime.timedelta(days=120)).isoformat()
    
    donors = [
        # Donor 1: Donated 10 days ago (in cooldown)
        {
            "id": 1, "full_name": "In Cooldown Donor",
            "blood_group": "O+", "profile_status": "ACTIVE",
            "next_verification_date": future, "last_verified_date": now.isoformat(),
            "last_donation_date": (now - datetime.timedelta(days=10)).isoformat(),
            "availability": "24_HOURS", "is_available": 1,
            "latitude": 22.5805, "longitude": 88.4344, "maximum_travel_distance": 25.0
        },
        # Donor 2: Donated 70 days ago (past 56-day cooldown)
        {
            "id": 2, "full_name": "Eligible Donor",
            "blood_group": "O+", "profile_status": "ACTIVE",
            "next_verification_date": future, "last_verified_date": now.isoformat(),
            "last_donation_date": (now - datetime.timedelta(days=70)).isoformat(),
            "availability": "24_HOURS", "is_available": 1,
            "latitude": 22.5805, "longitude": 88.4344, "maximum_travel_distance": 25.0
        }
    ]
    
    req = {
        "required_blood_group": "O+",
        "latitude": 22.5697,
        "longitude": 88.4046,
        "preferred_max_distance": 20.0,
        "required_date_time": now.isoformat(),
        "donation_cooldown_days": 56
    }
    
    results = run_matching_pipeline(req, donors, now_dt=now)
    assert len(results) == 1
    assert results[0]["donor_id"] == 2


# -------------------------------------------------------------
# PRIORITY 3: Missing next_verification_date Handling
# -------------------------------------------------------------

def test_missing_next_verification_date_returns_unknown_status():
    """Verify compute_lifecycle_status returns UNKNOWN when date is None."""
    assert compute_lifecycle_status(None) == "UNKNOWN"

def test_missing_next_verification_date_explicitly_handled_and_excluded(caplog):
    """Verify donors with missing next_verification_date are excluded with explicit state."""
    import logging
    candidates = [
        {"id": 1, "next_verification_date": None},
        {"id": 2, "next_verification_date": ""}
    ]
    with caplog.at_level(logging.WARNING):
        valid = filter_by_verification_status(candidates)
        assert len(valid) == 0
        # Verify warning log was emitted
        assert any("UNKNOWN" in record.message for record in caplog.records)


# -------------------------------------------------------------
# PRIORITY 4: Six-Month Verification Lifecycle & Grace Period
# -------------------------------------------------------------

def test_verification_lifecycle_configurable_grace_period():
    """Test transitions: ACTIVE -> VERIFICATION_DUE -> INACTIVE with configurable grace days."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Due date is 10 days in the past
    past_due_date = now - datetime.timedelta(days=10)
    
    # With grace_days=15: 10 days elapsed <= 15 days grace -> VERIFICATION_DUE
    assert compute_lifecycle_status(past_due_date, current_dt=now, grace_days=15) == "VERIFICATION_DUE"
    
    # With grace_days=5: 10 days elapsed > 5 days grace -> INACTIVE
    assert compute_lifecycle_status(past_due_date, current_dt=now, grace_days=5) == "INACTIVE"
    
    # With default grace_days=30: 10 days elapsed <= 30 days grace -> VERIFICATION_DUE
    assert compute_lifecycle_status(past_due_date, current_dt=now, grace_days=30) == "VERIFICATION_DUE"


# -------------------------------------------------------------
# PRIORITY 5: Transparent Scoring & Distance Double-Count Fix
# -------------------------------------------------------------

def test_calculate_matching_score_no_double_counting_and_weights_sum():
    """Verify ranking weights and that distance is not double counted."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Ideal donor at distance 0, 24h available (score 1.0), verified today (freshness 1.0)
    ideal_donor = {
        "id": 1,
        "distance_km": 0.0,
        "donor_max_travel": 25.0,
        "availability_score": 1.0,
        "last_verified_date": now.isoformat()
    }
    
    score, breakdown = calculate_matching_score(
        ideal_donor,
        patient_max_dist=25.0,
        urgency="NORMAL",
        now_dt=now
    )
    
    # Weights: Availability 35%, Distance 40%, Freshness 25% -> exactly 100.0
    assert score == 100.0
    assert breakdown["availability_score"] == 100.0
    assert breakdown["distance_score"] == 100.0
    assert breakdown["verification_freshness_score"] == 100.0

def test_calculate_matching_score_urgency_modifier():
    """Verify urgency modifier scales distance factor under CRITICAL/URGENT searches."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    donor = {
        "id": 1,
        "distance_km": 10.0,
        "donor_max_travel": 25.0,
        "availability_score": 1.0,
        "last_verified_date": now.isoformat()
    }
    
    score_normal, _ = calculate_matching_score(donor, patient_max_dist=25.0, urgency="NORMAL", now_dt=now)
    score_critical, _ = calculate_matching_score(donor, patient_max_dist=25.0, urgency="CRITICAL", now_dt=now)
    
    # In CRITICAL urgency, proximity factor receives 1.2 multiplier -> higher overall score
    assert score_critical > score_normal
