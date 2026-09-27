"""
Bridge module: Delegates verification logic to models/donor.py and matching/filters.py.
Maintains 100% backward compatibility for existing tests.
"""
from matching.filters import parse_iso_datetime, compute_lifecycle_status
from models.donor import DonorModel

def refresh_donor_verification(user_id, interval_days=None, db=None):
    return DonorModel.confirm_verification(user_id, db=db)

def get_donor_verification_details(user_id, db=None):
    return DonorModel.get_verification_lifecycle(user_id, db=db)

def sweep_and_update_donor_statuses(db=None):
    updated = DonorModel.sweep_statuses(db=db)
    return {"updated": updated}

__all__ = [
    "parse_iso_datetime",
    "compute_lifecycle_status",
    "refresh_donor_verification",
    "get_donor_verification_details",
    "sweep_and_update_donor_statuses"
]
