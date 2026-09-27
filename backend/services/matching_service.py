"""
Bridge module: Delegates matching logic to the new modular matching/ package.
Maintains 100% backward compatibility for existing imports and test fixtures.
"""
from matching.distance import calculate_distance_km as haversine_distance_km
from matching.availability import check_availability
from matching.ranking import calculate_verification_recency_score
from matching.matcher import find_matching_donors
from matching.filters import filter_by_donation_cooldown

def is_availability_satisfied(donor_availability, target_datetime=None):
    """Bridge for legacy availability test calls."""
    ok, score, _ = check_availability(donor_availability, target_datetime=target_datetime)
    return ok, score

__all__ = [
    "haversine_distance_km",
    "is_availability_satisfied",
    "calculate_verification_recency_score",
    "find_matching_donors",
    "filter_by_donation_cooldown"
]
