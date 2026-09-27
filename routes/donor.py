"""
HEMONEXAS Donor Blueprint
Handles donor profile management, 6-month verification renewals,
temporary availability toggling, incoming blood request responses,
and donation history.
"""
import datetime
from flask import Blueprint, request, jsonify, session
from routes.auth import login_required, role_required
from database.db import get_db, query_db, execute_db
from models.donor import DonorModel
from models.notification import NotificationModel

donor_bp = Blueprint("donor", __name__)

VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
VALID_AVAILABILITIES = ("24_HOURS", "8_HOURS", "DAY", "NIGHT", "DAYTIME", "NIGHTTIME")

@donor_bp.route("/api/donor/profile", methods=["GET"])
@role_required("donor", "admin")
def get_donor_profile():
    """Get own donor profile with verification lifecycle details."""
    user_id = session["user_id"]
    conn = get_db()
    profile = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    
    if not profile:
        return jsonify({"success": False, "error": "Donor profile not found."}), 404
        
    verification = DonorModel.get_verification_lifecycle(user_id, db=conn)
    return jsonify({
        "success": True,
        "profile": profile,
        "verification": verification
    }), 200

@donor_bp.route("/api/donor/profile", methods=["POST", "PUT", "PATCH"])
@role_required("donor")
def save_donor_profile():
    """Create or update donor profile with availability and travel limits."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    blood_group = (data.get("blood_group") or "").strip().upper()
    phone = (data.get("phone") or "").strip()
    location = (data.get("location") or "").strip()
    availability = (data.get("availability") or "24_HOURS").strip().upper()
    available_from = data.get("available_from", "00:00")
    available_to = data.get("available_to", "23:59")
    
    # Temporary availability toggle
    is_available = data.get("is_available")
    if is_available is not None:
        try:
            is_available = 1 if int(is_available) == 1 or str(is_available).lower() == "true" else 0
        except (ValueError, TypeError):
            is_available = 1
    else:
        is_available = 1
    
    try:
        max_dist = float(data.get("maximum_travel_distance", 15.0))
        if max_dist <= 0:
            max_dist = 15.0
    except (ValueError, TypeError):
        max_dist = 15.0
        
    lat = data.get("latitude")
    lon = data.get("longitude")
    try:
        lat = float(lat) if lat is not None and lat != "" else None
    except ValueError:
        lat = None
        
    try:
        lon = float(lon) if lon is not None and lon != "" else None
    except ValueError:
        lon = None
        
    if blood_group and blood_group not in VALID_BLOOD_GROUPS:
        return jsonify({"success": False, "error": f"Invalid blood group '{blood_group}'."}), 400
        
    if availability and availability not in VALID_AVAILABILITIES:
        return jsonify({"success": False, "error": f"Invalid availability pattern '{availability}'."}), 400

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    existing = query_db("SELECT id FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    
    if existing:
        execute_db(
            """UPDATE donor_profiles 
               SET blood_group = COALESCE(NULLIF(?, ''), blood_group),
                   phone = COALESCE(NULLIF(?, ''), phone),
                   location = COALESCE(NULLIF(?, ''), location),
                   latitude = COALESCE(?, latitude),
                   longitude = COALESCE(?, longitude),
                   availability = COALESCE(NULLIF(?, ''), availability),
                   available_from = COALESCE(NULLIF(?, ''), available_from),
                   available_to = COALESCE(NULLIF(?, ''), available_to),
                   maximum_travel_distance = COALESCE(?, maximum_travel_distance),
                   is_available = COALESCE(?, is_available),
                   updated_at = ?
               WHERE user_id = ?""",
            (blood_group, phone, location, lat, lon, availability, available_from, available_to, max_dist, is_available, now, user_id),
            db=conn
        )
        msg = "Donor profile updated successfully."
    else:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        next_due = (now_dt + datetime.timedelta(days=180)).isoformat()
        execute_db(
            """INSERT INTO donor_profiles 
               (user_id, blood_group, phone, location, latitude, longitude, availability, available_from, available_to, maximum_travel_distance, is_available, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?)""",
            (user_id, blood_group or "O+", phone or "", location or "", lat, lon, availability, available_from, available_to, max_dist, is_available, now, next_due, now, now),
            db=conn
        )
        msg = "Donor profile created successfully."

    profile = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    verification = DonorModel.get_verification_lifecycle(user_id, db=conn)
    
    return jsonify({
        "success": True,
        "message": msg,
        "profile": profile,
        "verification": verification
    }), 200

@donor_bp.route("/api/donor/availability/toggle", methods=["POST"])
@role_required("donor")
def toggle_availability():
    """Toggles donor between available and temporarily unavailable."""
    user_id = session["user_id"]
    conn = get_db()
    profile = query_db("SELECT is_available FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    if not profile:
        return jsonify({"success": False, "error": "Donor profile not found."}), 404
        
    new_state = 0 if profile["is_available"] == 1 else 1
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db("UPDATE donor_profiles SET is_available = ?, updated_at = ? WHERE user_id = ?", (new_state, now, user_id), db=conn)
    
    state_label = "Available for blood requests" if new_state == 1 else "Temporarily Unavailable"
    return jsonify({
        "success": True,
        "is_available": new_state,
        "message": f"Availability status updated: {state_label}."
    }), 200

@donor_bp.route("/api/donor/profile/verify", methods=["POST"])
@role_required("donor")
def verify_profile():
    """
    Donor confirmation endpoint for 6-month verification cycle.
    Resets status to ACTIVE, updates last_verified_date to now and next_verification_date to +180 days.
    Allows inactive donors to re-verify and become active again.
    """
    user_id = session["user_id"]
    conn = get_db()
    result = DonorModel.confirm_verification(user_id, db=conn)
    
    if not result:
        return jsonify({"success": False, "error": "Unable to verify profile."}), 404
        
    return jsonify({
        "success": True,
        "message": "Donor profile successfully re-verified! Your status is now ACTIVE for the next 6 months.",
        "verification": result
    }), 200

@donor_bp.route("/api/donor/status", methods=["GET"])
@role_required("donor", "admin")
def check_donor_status():
    """Get verification status and remaining grace period."""
    user_id = session["user_id"]
    conn = get_db()
    details = DonorModel.get_verification_lifecycle(user_id, db=conn)
    if not details:
        return jsonify({"success": False, "error": "Donor profile not found."}), 404
    return jsonify({"success": True, "status": details}), 200

@donor_bp.route("/api/donor/requests", methods=["GET"])
@role_required("donor")
def get_donor_requests():
    """List incoming blood donation requests sent to this donor."""
    donor_user_id = session["user_id"]
    conn = get_db()
    
    sql = """
        SELECT r.id AS response_id, r.status AS response_status, r.message AS response_message,
               r.response_time, r.created_at AS requested_at,
               br.id AS blood_request_id, br.required_blood_group, br.required_units,
               br.hospital_name, br.location AS hospital_location, br.urgency,
               br.request_status, br.required_date_time,
               u.full_name AS patient_name, u.email AS patient_email
        FROM donor_request_responses r
        JOIN blood_requests br ON r.blood_request_id = br.id
        JOIN users u ON br.patient_id = u.id
        WHERE r.donor_id = ?
        ORDER BY 
            CASE r.status WHEN 'PENDING' THEN 1 ELSE 2 END,
            r.created_at DESC
    """
    requests = query_db(sql, (donor_user_id,), db=conn)
    return jsonify({"success": True, "requests": requests}), 200

@donor_bp.route("/api/donor/requests/<int:response_id>/accept", methods=["POST"])
@role_required("donor")
def accept_request(response_id):
    """Donor accepts an incoming blood donation request."""
    donor_user_id = session["user_id"]
    donor_name = session.get("user_name", "A Donor")
    data = request.get_json(silent=True) or request.form.to_dict()
    optional_message = data.get("message", "I am available and ready to donate.")
    conn = get_db()
    
    resp = query_db(
        """SELECT r.*, br.patient_id, br.hospital_name 
           FROM donor_request_responses r
           JOIN blood_requests br ON r.blood_request_id = br.id
           WHERE r.id = ? AND r.donor_id = ?""",
        (response_id, donor_user_id),
        one=True,
        db=conn
    )
    if not resp:
        return jsonify({"success": False, "error": "Donation request not found or access unauthorized."}), 404
        
    if resp["status"] == "ACCEPTED":
        return jsonify({"success": True, "message": "Request is already accepted."}), 200
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        "UPDATE donor_request_responses SET status = 'ACCEPTED', response_time = ?, message = ?, updated_at = ? WHERE id = ?",
        (now, optional_message, now, response_id),
        db=conn
    )
    
    execute_db(
        "UPDATE blood_requests SET request_status = 'MATCHING', updated_at = ? WHERE id = ? AND request_status = 'OPEN'",
        (now, resp["blood_request_id"]),
        db=conn
    )
    
    # Notify patient
    NotificationModel.create(
        user_id=resp["patient_id"],
        title="Donation Request Accepted!",
        message=f"{donor_name} accepted your blood donation request for {resp['hospital_name']}.",
        notif_type="SUCCESS",
        link="/patient/dashboard",
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (donor_user_id, "DONATION_ACCEPTED", f"Accepted blood request #{resp['blood_request_id']}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": "Blood donation request accepted successfully. Thank you for saving a life!",
        "response_id": response_id,
        "status": "ACCEPTED"
    }), 200

@donor_bp.route("/api/donor/requests/<int:response_id>/reject", methods=["POST"])
@role_required("donor")
def reject_request(response_id):
    """Donor declines an incoming blood donation request."""
    donor_user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    optional_message = data.get("message", "Declined due to schedule or unavailability.")
    conn = get_db()
    
    resp = query_db(
        """SELECT r.*, br.patient_id, br.hospital_name 
           FROM donor_request_responses r
           JOIN blood_requests br ON r.blood_request_id = br.id
           WHERE r.id = ? AND r.donor_id = ?""",
        (response_id, donor_user_id),
        one=True,
        db=conn
    )
    if not resp:
        return jsonify({"success": False, "error": "Donation request not found or access unauthorized."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        "UPDATE donor_request_responses SET status = 'REJECTED', response_time = ?, message = ?, updated_at = ? WHERE id = ?",
        (now, optional_message, now, response_id),
        db=conn
    )
    
    # Notify patient
    NotificationModel.create(
        user_id=resp["patient_id"],
        title="Donation Request Update",
        message=f"A contacted donor was unable to fulfill your request for {resp['hospital_name']}.",
        notif_type="INFO",
        link="/patient/dashboard",
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (donor_user_id, "DONATION_REJECTED", f"Declined blood request #{resp['blood_request_id']}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": "Donation request declined.",
        "response_id": response_id,
        "status": "REJECTED"
    }), 200

@donor_bp.route("/api/donor/history", methods=["GET"])
@role_required("donor")
def get_donation_history():
    """Lists official donation records completed by this donor at certified blood centers."""
    donor_user_id = session["user_id"]
    conn = get_db()
    sql = """
        SELECT dr.*, u.full_name AS patient_name
        FROM donation_records dr
        LEFT JOIN users u ON dr.patient_id = u.id
        WHERE dr.donor_id = ?
        ORDER BY dr.donation_date DESC
    """
    records = query_db(sql, (donor_user_id,), db=conn)
    return jsonify({"success": True, "history": records}), 200
