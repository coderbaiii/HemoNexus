import datetime
from flask import Blueprint, request, jsonify, session
from backend.routes.auth import login_required, role_required
from backend.database import get_db, query_db, execute_db
from backend.services.matching_service import find_matching_donors

patient_bp = Blueprint("patient", __name__)

VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
VALID_URGENCIES = ("LOW", "NORMAL", "URGENT", "CRITICAL")

@patient_bp.route("/api/patient/profile", methods=["GET"])
@role_required("patient", "admin")
def get_patient_profile():
    """Fetch patient profile."""
    user_id = session["user_id"]
    conn = get_db()
    profile = query_db("SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    return jsonify({"success": True, "profile": profile}), 200

@patient_bp.route("/api/patient/profile", methods=["POST", "PUT", "PATCH"])
@role_required("patient")
def update_patient_profile():
    """Create or update patient profile."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    phone = (data.get("phone") or "").strip()
    location = (data.get("location") or "").strip()
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
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    existing = query_db("SELECT id FROM patient_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    
    if existing:
        execute_db(
            """UPDATE patient_profiles 
               SET phone = COALESCE(NULLIF(?, ''), phone),
                   location = COALESCE(NULLIF(?, ''), location),
                   latitude = COALESCE(?, latitude),
                   longitude = COALESCE(?, longitude),
                   updated_at = ?
               WHERE user_id = ?""",
            (phone, location, lat, lon, now, user_id),
            db=conn
        )
    else:
        execute_db(
            "INSERT INTO patient_profiles (user_id, phone, location, latitude, longitude, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, phone, location, lat, lon, now, now),
            db=conn
        )
        
    profile = query_db("SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    return jsonify({"success": True, "message": "Patient profile updated.", "profile": profile}), 200

@patient_bp.route("/api/patient/blood-requests", methods=["POST"])
@role_required("patient")
def create_blood_request():
    """Create a new requirement-based blood request."""
    patient_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    
    blood_group = (data.get("required_blood_group") or "").strip().upper()
    hospital_name = (data.get("hospital_name") or "").strip()
    location = (data.get("location") or "").strip()
    urgency = (data.get("urgency") or "NORMAL").strip().upper()
    req_date_time = data.get("required_date_time")
    
    try:
        units = int(data.get("required_units", 1))
        if units <= 0:
            units = 1
    except (ValueError, TypeError):
        units = 1
        
    try:
        pref_dist = float(data.get("preferred_max_distance", 25.0))
        if pref_dist <= 0:
            pref_dist = 25.0
    except (ValueError, TypeError):
        pref_dist = 25.0
        
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
        
    if not blood_group or blood_group not in VALID_BLOOD_GROUPS:
        return jsonify({"success": False, "error": f"Invalid or missing required blood group '{blood_group}'."}), 400
        
    if not hospital_name:
        return jsonify({"success": False, "error": "Hospital name is required."}), 400
        
    if urgency not in VALID_URGENCIES:
        urgency = "NORMAL"
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if not req_date_time:
        req_date_time = now
        
    conn = get_db()
    req_id, _ = execute_db(
        """INSERT INTO blood_requests 
           (patient_id, required_blood_group, required_units, hospital_name, location, latitude, longitude, preferred_max_distance, required_date_time, urgency, request_status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)""",
        (patient_id, blood_group, units, hospital_name, location or hospital_name, lat, lon, pref_dist, req_date_time, urgency, now, now),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (patient_id, "BLOOD_REQUEST_CREATED", f"Created {blood_group} request #{req_id} for {hospital_name}"),
        db=conn
    )
    
    req_record = query_db("SELECT * FROM blood_requests WHERE id = ?", (req_id,), one=True, db=conn)
    return jsonify({
        "success": True,
        "message": "Blood request created successfully. Smart matching is ready.",
        "request": req_record
    }), 201

@patient_bp.route("/api/patient/blood-requests", methods=["GET"])
@role_required("patient")
def list_patient_requests():
    """List all blood requests created by the logged in patient."""
    patient_id = session["user_id"]
    conn = get_db()
    
    requests = query_db(
        """SELECT br.*, 
                  COUNT(r.id) AS total_sent,
                  SUM(CASE WHEN r.status = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_count,
                  SUM(CASE WHEN r.status = 'PENDING' THEN 1 ELSE 0 END) AS pending_count
           FROM blood_requests br
           LEFT JOIN donor_request_responses r ON br.id = r.blood_request_id
           WHERE br.patient_id = ?
           GROUP BY br.id
           ORDER BY br.created_at DESC""",
        (patient_id,),
        db=conn
    )
    return jsonify({"success": True, "requests": requests}), 200

@patient_bp.route("/api/patient/blood-requests/<int:request_id>", methods=["GET"])
@role_required("patient", "admin")
def get_request_details(request_id):
    """Get single blood request details along with donor responses."""
    user_id = session["user_id"]
    role = session.get("role")
    conn = get_db()
    
    req_row = query_db("SELECT * FROM blood_requests WHERE id = ?", (request_id,), one=True, db=conn)
    if not req_row:
        return jsonify({"success": False, "error": "Blood request not found."}), 404
        
    if role != "admin" and req_row["patient_id"] != user_id:
        return jsonify({"success": False, "error": "Forbidden: Not your blood request."}), 403
        
    responses = query_db(
        """SELECT r.id, r.status, r.response_time, r.message, r.created_at,
                  u.full_name AS donor_name, u.email AS donor_email,
                  d.blood_group AS donor_blood_group, d.phone AS donor_phone
           FROM donor_request_responses r
           JOIN users u ON r.donor_id = u.id
           LEFT JOIN donor_profiles d ON u.id = d.user_id
           WHERE r.blood_request_id = ?
           ORDER BY r.created_at DESC""",
        (request_id,),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "request": req_row,
        "responses": responses
    }), 200

@patient_bp.route("/api/patient/blood-requests/<int:request_id>/matches", methods=["GET"])
@role_required("patient", "admin")
def get_matches_for_request(request_id):
    """
    Invokes the smart matching engine to find and rank active donors for a blood request.
    """
    user_id = session["user_id"]
    role = session.get("role")
    conn = get_db()
    
    req_row = query_db("SELECT * FROM blood_requests WHERE id = ?", (request_id,), one=True, db=conn)
    if not req_row:
        return jsonify({"success": False, "error": "Blood request not found."}), 404
        
    if role != "admin" and req_row["patient_id"] != user_id:
        return jsonify({"success": False, "error": "Forbidden: Not your blood request."}), 403
        
    matches = find_matching_donors(request_id, db=conn)
    
    return jsonify({
        "success": True,
        "request_id": request_id,
        "required_blood_group": req_row["required_blood_group"],
        "total_matches": len(matches),
        "matches": matches
    }), 200

@patient_bp.route("/api/patient/blood-requests/<int:request_id>/send-request", methods=["POST"])
@role_required("patient")
def send_donor_request(request_id):
    """
    Patient sends a blood donation invitation to a specific matching donor.
    Prevents duplicate active requests.
    """
    patient_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    req_row = query_db("SELECT * FROM blood_requests WHERE id = ? AND patient_id = ?", (request_id, patient_id), one=True, db=conn)
    if not req_row:
        return jsonify({"success": False, "error": "Blood request not found or unauthorized."}), 404
        
    if req_row["request_status"] in ("FULFILLED", "CANCELLED"):
        return jsonify({"success": False, "error": f"Cannot send requests for a {req_row['request_status']} blood requirement."}), 400
        
    donor_user_id = data.get("donor_id")
    if not donor_user_id:
        return jsonify({"success": False, "error": "donor_id is required."}), 400
        
    # Check if donor_id is a user_id or a donor_profile id
    donor_user = query_db("SELECT id, role FROM users WHERE id = ?", (donor_user_id,), one=True, db=conn)
    if not donor_user or donor_user["role"] != "donor":
        # Check if they passed donor_profile id
        profile = query_db("SELECT user_id FROM donor_profiles WHERE id = ?", (donor_user_id,), one=True, db=conn)
        if profile:
            donor_user_id = profile["user_id"]
        else:
            return jsonify({"success": False, "error": "Specified donor was not found."}), 404
            
    # Check for duplicate request
    existing = query_db(
        "SELECT id, status FROM donor_request_responses WHERE blood_request_id = ? AND donor_id = ?",
        (request_id, donor_user_id),
        one=True,
        db=conn
    )
    if existing:
        return jsonify({
            "success": False, 
            "error": f"A donation request has already been sent to this donor (current status: {existing['status']})."
        }), 409
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    resp_id, _ = execute_db(
        """INSERT INTO donor_request_responses 
           (blood_request_id, donor_id, status, created_at, updated_at)
           VALUES (?, ?, 'PENDING', ?, ?)""",
        (request_id, donor_user_id, now, now),
        db=conn
    )
    
    # Update request status to MATCHING if still OPEN
    execute_db(
        "UPDATE blood_requests SET request_status = 'MATCHING', updated_at = ? WHERE id = ? AND request_status = 'OPEN'",
        (now, request_id),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (patient_id, "DONATION_REQUEST_DISPATCHED", f"Dispatched request #{request_id} to donor user #{donor_user_id}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": "Donation request sent to the donor successfully.",
        "response_id": resp_id,
        "status": "PENDING"
    }), 201

@patient_bp.route("/api/patient/blood-requests/<int:request_id>/cancel", methods=["PATCH", "POST"])
@role_required("patient", "admin")
def cancel_blood_request(request_id):
    """Patient or admin cancels a blood request."""
    user_id = session["user_id"]
    role = session.get("role")
    conn = get_db()
    
    req_row = query_db("SELECT * FROM blood_requests WHERE id = ?", (request_id,), one=True, db=conn)
    if not req_row:
        return jsonify({"success": False, "error": "Blood request not found."}), 404
        
    if role != "admin" and req_row["patient_id"] != user_id:
        return jsonify({"success": False, "error": "Forbidden: Not your blood request."}), 403
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db("UPDATE blood_requests SET request_status = 'CANCELLED', updated_at = ? WHERE id = ?", (now, request_id), db=conn)
    
    # Also cancel pending donor responses
    execute_db(
        "UPDATE donor_request_responses SET status = 'CANCELLED', updated_at = ? WHERE blood_request_id = ? AND status = 'PENDING'",
        (now, request_id),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, "BLOOD_REQUEST_CANCELLED", f"Blood request #{request_id} was cancelled"),
        db=conn
    )
    
    return jsonify({"success": True, "message": "Blood request cancelled successfully."}), 200

@patient_bp.route("/api/patient/blood-requests/<int:request_id>/fulfill", methods=["PATCH", "POST"])
@role_required("patient", "admin")
def fulfill_blood_request(request_id):
    """Mark a blood request as fulfilled."""
    user_id = session["user_id"]
    role = session.get("role")
    conn = get_db()
    
    req_row = query_db("SELECT * FROM blood_requests WHERE id = ?", (request_id,), one=True, db=conn)
    if not req_row:
        return jsonify({"success": False, "error": "Blood request not found."}), 404
        
    if role != "admin" and req_row["patient_id"] != user_id:
        return jsonify({"success": False, "error": "Forbidden: Not your blood request."}), 403
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db("UPDATE blood_requests SET request_status = 'FULFILLED', updated_at = ? WHERE id = ?", (now, request_id), db=conn)
    
    return jsonify({"success": True, "message": "Blood request marked as fulfilled."}), 200
