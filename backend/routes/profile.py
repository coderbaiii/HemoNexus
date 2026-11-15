import re
import datetime
from flask import Blueprint, request, jsonify, session
from backend.routes.auth import login_required, EMAIL_REGEX
from backend.database import get_db, query_db, execute_db

profile_bp = Blueprint("profile", __name__)

VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
VALID_AVAILABILITIES = ("24_HOURS", "8_HOURS", "DAYTIME", "NIGHTTIME", "TEMPORARILY_UNAVAILABLE")

@profile_bp.route("/api/profile", methods=["GET"])
@login_required
def get_user_profile():
    """Retrieve full unified profile details for the authenticated user."""
    user_id = session["user_id"]
    conn = get_db()
    
    user = query_db(
        "SELECT id, full_name, email, role, phone, profile_photo, address, city, created_at, updated_at FROM users WHERE id = ?",
        (user_id,),
        one=True,
        db=conn
    )
    if not user:
        return jsonify({"success": False, "error": "User account not found."}), 404
        
    role = user["role"].lower()
    donor_profile = None
    patient_profile = None
    ngo_profile = None
    
    if role == "donor":
        donor_profile = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    elif role == "patient":
        patient_profile = query_db("SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    elif role == "ngo":
        ngo_profile = query_db("SELECT * FROM ngo_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
        
    # Blocked accounts count
    blocked_count = query_db("SELECT COUNT(*) AS count FROM blocked_users WHERE blocker_id = ?", (user_id,), one=True, db=conn)
    
    # Blood group to return
    blood_group = "O+"
    availability = "24_HOURS"
    if donor_profile:
        blood_group = donor_profile.get("blood_group") or "O+"
        availability = donor_profile.get("availability") or "24_HOURS"
        
    return jsonify({
        "success": True,
        "user": user,
        "blood_group": blood_group,
        "availability": availability,
        "donor_profile": donor_profile,
        "patient_profile": patient_profile,
        "ngo_profile": ngo_profile,
        "blocked_accounts_count": blocked_count["count"] if blocked_count else 0
    }), 200

@profile_bp.route("/api/profile", methods=["POST", "PUT"])
@login_required
def update_user_profile():
    """Update profile fields with validation and session synchronization."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True, db=conn)
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404
        
    full_name = (data.get("full_name") or user["full_name"]).strip()
    email = (data.get("email") or user["email"]).strip().lower()
    phone = (data.get("phone") if "phone" in data else user["phone"]) or ""
    phone = phone.strip()
    address = (data.get("address") if "address" in data else user["address"]) or ""
    address = address.strip()
    city = (data.get("city") if "city" in data else user["city"]) or "Kolkata"
    city = city.strip()
    profile_photo = data.get("profile_photo", user.get("profile_photo"))
    if profile_photo:
        profile_photo = str(profile_photo).strip() or None
        
    # Validation
    if not full_name:
        return jsonify({"success": False, "error": "Full name cannot be empty."}), 400
        
    if not re.match(EMAIL_REGEX, email):
        return jsonify({"success": False, "error": "Invalid email address format."}), 400
        
    # Email duplicate check if changed
    if email != user["email"].lower():
        existing_email = query_db("SELECT id FROM users WHERE email = ? AND id != ?", (email, user_id), one=True, db=conn)
        if existing_email:
            return jsonify({"success": False, "error": f"Email '{email}' is already in use by another account."}), 409
            
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Update users table
    execute_db(
        """UPDATE users
           SET full_name = ?,
               email = ?,
               phone = ?,
               address = ?,
               city = ?,
               profile_photo = ?,
               updated_at = ?
           WHERE id = ?""",
        (full_name, email, phone, address, city, profile_photo, now, user_id),
        db=conn
    )
    
    # Update role-specific profile
    role = user["role"].lower()
    blood_group = data.get("blood_group")
    if blood_group:
        blood_group = blood_group.strip().upper()
        if blood_group not in VALID_BLOOD_GROUPS:
            return jsonify({"success": False, "error": f"Invalid blood group '{blood_group}'."}), 400
            
    availability = data.get("availability")
    if availability:
        availability = availability.strip().upper()
        if availability not in VALID_AVAILABILITIES:
            return jsonify({"success": False, "error": f"Invalid availability option '{availability}'."}), 400
            
    if role == "donor":
        # Check if donor profile exists
        dp = query_db("SELECT id FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
        if dp:
            execute_db(
                """UPDATE donor_profiles
                   SET phone = ?,
                       location = ?,
                       blood_group = COALESCE(?, blood_group),
                       availability = COALESCE(?, availability),
                       updated_at = ?
                   WHERE user_id = ?""",
                (phone, city, blood_group, availability, now, user_id),
                db=conn
            )
        else:
            next_due = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=180)).isoformat()
            execute_db(
                """INSERT INTO donor_profiles 
                   (user_id, blood_group, phone, location, availability, maximum_travel_distance, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 15.0, 'ACTIVE', ?, ?, ?, ?)""",
                (user_id, blood_group or "O+", phone, city, availability or "24_HOURS", now, next_due, now, now),
                db=conn
            )
    elif role == "patient":
        pp = query_db("SELECT id FROM patient_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
        if pp:
            execute_db(
                """UPDATE patient_profiles
                   SET phone = ?,
                       location = ?,
                       updated_at = ?
                   WHERE user_id = ?""",
                (phone, city, now, user_id),
                db=conn
            )
        else:
            execute_db(
                "INSERT INTO patient_profiles (user_id, phone, location, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, phone, city, now, now),
                db=conn
            )
            
    # Keep session in sync
    session["user_name"] = full_name
    session["user_email"] = email
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, "PROFILE_UPDATED", f"User {email} updated profile details"),
        db=conn
    )
    
    updated_user = query_db(
        "SELECT id, full_name, email, role, phone, profile_photo, address, city FROM users WHERE id = ?",
        (user_id,),
        one=True,
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": "Profile updated successfully.",
        "user": updated_user
    }), 200
