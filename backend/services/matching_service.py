"""
HEMONEXAS Matching Service Bridge
Delegates matching logic to the modular matching/ package (Member 3 responsibility).
Maintains 100% backward compatibility for all backend routes and integration tests.
"""
from matching.distance import calculate_distance_km as haversine_distance_km, estimate_travel_time_minutes
from matching.availability import check_availability, is_time_in_range
from matching.ranking import calculate_verification_recency_score, calculate_matching_score
from matching.matcher import find_matching_donors, run_matching_pipeline, MEDICAL_SAFETY_DISCLAIMER
from matching.filters import (
    filter_by_blood_group,
    filter_by_active_status,
    filter_by_verification_status,
    filter_by_donation_cooldown,
    filter_by_temporary_availability,
    filter_by_availability_schedule,
    filter_by_patient_distance,
    filter_by_donor_travel_limit
)

def is_availability_satisfied(donor_availability, target_datetime=None):
    """Bridge for legacy availability test calls."""
    ok, score, _ = check_availability(donor_availability, target_datetime=target_datetime)
    return ok, score

__all__ = [
    "haversine_distance_km",
    "estimate_travel_time_minutes",
    "is_availability_satisfied",
    "is_time_in_range",
    "calculate_verification_recency_score",
    "calculate_matching_score",
    "find_matching_donors",
    "run_matching_pipeline",
    "filter_by_blood_group",
    "filter_by_active_status",
    "filter_by_verification_status",
    "filter_by_donation_cooldown",
    "filter_by_temporary_availability",
    "filter_by_availability_schedule",
    "filter_by_patient_distance",
    "filter_by_donor_travel_limit",
    "MEDICAL_SAFETY_DISCLAIMER"
]
