import datetime
from flask import Blueprint, request, jsonify, session
from backend.routes.auth import login_required, role_required
from backend.database import get_db, query_db, execute_db
from backend.services.verification_service import refresh_donor_verification, get_donor_verification_details

donor_bp = Blueprint("donor", __name__)

VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
VALID_AVAILABILITIES = ("24_HOURS", "8_HOURS", "DAYTIME", "NIGHTTIME")

@donor_bp.route("/api/donor/profile", methods=["GET"])
@role_required("donor", "admin")
def get_donor_profile():
    """Get own donor profile with verification lifecycle details."""
    user_id = session["user_id"]
    conn = get_db()
    profile = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    
    if not profile:
        return jsonify({"success": False, "error": "Donor profile not found."}), 404
        
    verification = get_donor_verification_details(user_id, db=conn)
    return jsonify({
        "success": True,
        "profile": profile,
        "verification": verification
    }), 200

@donor_bp.route("/api/donor/profile", methods=["POST", "PUT", "PATCH"])
@role_required("donor")
def save_donor_profile():
    """Create or update donor profile."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    blood_group = (data.get("blood_group") or "").strip().upper()
    phone = (data.get("phone") or "").strip()
    location = (data.get("location") or "").strip()
    availability = (data.get("availability") or "24_HOURS").strip().upper()
    
    try:
        max_dist = float(data.get("maximum_travel_distance", 15.0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid maximum travel distance. Must be a positive number."}), 400
        
    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is not None and lat != "":
        try:
            lat = float(lat)
        except ValueError:
            lat = None
    else:
        lat = None
        
    if lon is not None and lon != "":
        try:
            lon = float(lon)
        except ValueError:
            lon = None
    else:
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
                   maximum_travel_distance = COALESCE(?, maximum_travel_distance),
                   updated_at = ?
               WHERE user_id = ?""",
            (blood_group, phone, location, lat, lon, availability, max_dist, now, user_id),
            db=conn
        )
        msg = "Donor profile updated successfully."
    else:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        next_due = (now_dt + datetime.timedelta(days=180)).isoformat()
        execute_db(
            """INSERT INTO donor_profiles 
               (user_id, blood_group, phone, location, latitude, longitude, availability, maximum_travel_distance, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?)""",
            (user_id, blood_group or "O+", phone or "", location or "", lat, lon, availability, max_dist, now, next_due, now, now),
            db=conn
        )
        msg = "Donor profile created successfully."

    profile = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    verification = get_donor_verification_details(user_id, db=conn)
    
    return jsonify({
        "success": True,
        "message": msg,
        "profile": profile,
        "verification": verification
    }), 200

@donor_bp.route("/api/donor/profile/verify", methods=["POST"])
@role_required("donor")
def verify_profile():
    """
    Donor confirmation endpoint for 6-month verification cycle.
    Resets status to ACTIVE, updates last_verified_date and next_verification_date.
    """
    user_id = session["user_id"]
    conn = get_db()
    result = refresh_donor_verification(user_id, db=conn)
    
    return jsonify({
        "success": True,
        "message": "Donor profile successfully re-verified. Your status is now ACTIVE for the next 6 months.",
        "verification": result
    }), 200

@donor_bp.route("/api/donor/status", methods=["GET"])
@role_required("donor", "admin")
def check_donor_status():
    """Get verification status and remaining grace period."""
    user_id = session["user_id"]
    conn = get_db()
    details = get_donor_verification_details(user_id, db=conn)
    if not details:
        return jsonify({"success": False, "error": "Donor profile not found."}), 404
    return jsonify({"success": True, "status": details}), 200

@donor_bp.route("/api/donor/requests", methods=["GET"])
@role_required("donor")
def get_donor_requests():
    """List incoming donation requests sent to this donor."""
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
    data = request.get_json(silent=True) or request.form.to_dict()
    optional_message = data.get("message", "I am available and ready to donate.")
    conn = get_db()
    
    resp = query_db(
        "SELECT * FROM donor_request_responses WHERE id = ? AND donor_id = ?",
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
    
    # Update blood request status to MATCHING if still OPEN
    execute_db(
        "UPDATE blood_requests SET request_status = 'MATCHING', updated_at = ? WHERE id = ? AND request_status = 'OPEN'",
        (now, resp["blood_request_id"]),
        db=conn
    )
    
    # Audit log
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
        "SELECT * FROM donor_request_responses WHERE id = ? AND donor_id = ?",
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
