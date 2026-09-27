"""
HEMONEXAS Modular Matching Engine Package
"""
from matching.distance import calculate_distance_km, estimate_travel_time_minutes
from matching.availability import check_availability, is_time_in_range
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
from matching.ranking import (
    rank_nearest,
    rank_fastest,
    rank_recently_verified,
    rank_best_match,
    calculate_matching_score,
    calculate_verification_recency_score
)
from matching.matcher import run_matching_pipeline, find_matching_donors, MEDICAL_SAFETY_DISCLAIMER

__all__ = [
    "calculate_distance_km",
    "estimate_travel_time_minutes",
    "check_availability",
    "is_time_in_range",
    "filter_by_blood_group",
    "filter_by_active_status",
    "filter_by_verification_status",
    "filter_by_donation_cooldown",
    "filter_by_temporary_availability",
    "filter_by_availability_schedule",
    "filter_by_patient_distance",
    "filter_by_donor_travel_limit",
    "rank_nearest",
    "rank_fastest",
    "rank_recently_verified",
    "rank_best_match",
    "calculate_matching_score",
    "calculate_verification_recency_score",
    "run_matching_pipeline",
    "find_matching_donors",
    "MEDICAL_SAFETY_DISCLAIMER"
]
