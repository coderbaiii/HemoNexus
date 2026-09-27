"""
HEMONEXAS Donor Model
Manages donor profiles, 6-month verification cycles, and status updates.
"""
import datetime
from config import Config
from database.db import query_db, execute_db
from matching.filters import parse_iso_datetime, compute_lifecycle_status

class DonorModel:
    """Operations on donor_profiles table and verification history."""

    @staticmethod
    def get_by_user_id(user_id, db=None):
        return query_db(
            """SELECT d.*, u.full_name, u.email 
               FROM donor_profiles d
               JOIN users u ON d.user_id = u.id
               WHERE d.user_id = ?""",
            (user_id,),
            one=True,
            db=db
        )

    @staticmethod
    def get_by_id(donor_id, db=None):
        return query_db(
            """SELECT d.*, u.full_name, u.email 
               FROM donor_profiles d
               JOIN users u ON d.user_id = u.id
               WHERE d.id = ?""",
            (donor_id,),
            one=True,
            db=db
        )

    @staticmethod
    def get_verification_lifecycle(user_id, db=None):
        """Calculates dynamic verification status and days remaining."""
        profile = DonorModel.get_by_user_id(user_id, db=db)
        if not profile:
            return None
            
        now = datetime.datetime.now(datetime.timezone.utc)
        next_dt = parse_iso_datetime(profile["next_verification_date"])
        
        status = compute_lifecycle_status(next_dt, current_dt=now, grace_days=Config.GRACE_PERIOD_DAYS)
        days_until_due = round((next_dt - now).total_seconds() / 86400.0, 1)
        grace_end = next_dt + datetime.timedelta(days=Config.GRACE_PERIOD_DAYS)
        grace_remaining = max(0.0, round((grace_end - now).total_seconds() / 86400.0, 1))
        
        return {
            "profile_status": status,
            "status": status,
            "current_status": status,
            "database_status": profile["profile_status"],
            "last_verified_date": profile["last_verified_date"],
            "next_verification_date": profile["next_verification_date"],
            "verification_interval_days": Config.VERIFICATION_INTERVAL_DAYS,
            "days_until_due": days_until_due,
            "grace_days_remaining": grace_remaining if status == "VERIFICATION_DUE" else 0.0,
            "is_action_required": status != "ACTIVE"
        }

    @staticmethod
    def confirm_verification(user_id, db=None):
        """
        Donor confirms and verifies their contact information.
        Resets last_verified_date to now, next_verification_date to now + 180 days,
        and ensures profile_status is set to ACTIVE.
        Records renewal in donor_verifications table.
        """
        profile = DonorModel.get_by_user_id(user_id, db=db)
        if not profile:
            return None
            
        now = datetime.datetime.now(datetime.timezone.utc)
        next_due = now + datetime.timedelta(days=Config.VERIFICATION_INTERVAL_DAYS)
        now_iso = now.isoformat()
        next_due_iso = next_due.isoformat()
        
        status_before = profile["profile_status"]
        
        execute_db(
            """UPDATE donor_profiles 
               SET last_verified_date = ?,
                   next_verification_date = ?,
                   profile_status = 'ACTIVE',
                   updated_at = ?
               WHERE user_id = ?""",
            (now_iso, next_due_iso, now_iso, user_id),
            db=db
        )
        
        # Record in verification history table
        execute_db(
            """INSERT INTO donor_verifications 
               (donor_id, verification_date, status_before, status_after, remarks)
               VALUES (?, ?, ?, 'ACTIVE', 'Donor self-confirmed profile and availability for the next 6 months')""",
            (user_id, now_iso, status_before),
            db=db
        )
        
        return {
            "profile_status": "ACTIVE",
            "status": "ACTIVE",
            "last_verified_date": now_iso,
            "next_verification_date": next_due_iso,
            "verification_interval_days": Config.VERIFICATION_INTERVAL_DAYS
        }

    @staticmethod
    def sweep_statuses(db=None):
        """
        Evaluates all donors and updates statuses (ACTIVE -> VERIFICATION_DUE -> INACTIVE).
        Never deletes inactive accounts.
        """
        donors = query_db("SELECT id, user_id, profile_status, next_verification_date FROM donor_profiles", db=db)
        now = datetime.datetime.now(datetime.timezone.utc)
        now_iso = now.isoformat()
        updated_count = 0
        
        for d in donors:
            next_dt = parse_iso_datetime(d["next_verification_date"])
            new_status = compute_lifecycle_status(next_dt, current_dt=now, grace_days=Config.GRACE_PERIOD_DAYS)
            if new_status != d["profile_status"]:
                execute_db(
                    "UPDATE donor_profiles SET profile_status = ?, updated_at = ? WHERE id = ?",
                    (new_status, now_iso, d["id"]),
                    db=db
                )
                updated_count += 1
                
        return updated_count
