import datetime
from flask import Blueprint, request, jsonify, session
from backend.routes.auth import login_required, role_required
from backend.database import get_db, query_db, execute_db

ngo_bp = Blueprint("ngo", __name__)

VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")

def mask_contact(phone, email):
    """Safeguards donor privacy by masking direct contact information."""
    masked_phone = "+91 ••••• ••••" if phone else "Not provided"
    if email and "@" in email:
        parts = email.split("@")
        masked_email = f"{parts[0][0]}••••@{parts[1]}"
    else:
        masked_email = "••••@••••.org"
    return masked_phone, masked_email

@ngo_bp.route("/api/ngo/profile", methods=["GET"])
@login_required
def get_ngo_profile():
    """Retrieve NGO profile for the current user."""
    user_id = session["user_id"]
    user_role = session.get("role", "").lower()
    if user_role not in ("ngo", "admin"):
        return jsonify({
            "success": False,
            "error": "Forbidden: The NGO profile and operations are reserved exclusively for registered blood donation NGOs."
        }), 403

    conn = get_db()
    
    profile = query_db(
        """SELECT np.*, u.full_name AS account_name, u.email AS account_email
           FROM ngo_profiles np
           JOIN users u ON np.user_id = u.id
           WHERE np.user_id = ?""",
        (user_id,),
        one=True,
        db=conn
    )
    
    if not profile:
        user = query_db("SELECT id, full_name, email, role, phone, address, city FROM users WHERE id = ?", (user_id,), one=True, db=conn)
        return jsonify({
            "success": True,
            "profile": None,
            "user": user,
            "is_ngo": True
        }), 200
        
    return jsonify({
        "success": True,
        "profile": profile,
        "is_verified": profile.get("verification_status") == "VERIFIED"
    }), 200

@ngo_bp.route("/api/ngo/profile", methods=["POST", "PUT"])
@role_required("ngo", "admin")
def save_ngo_profile():
    """Create or update NGO profile."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    ngo_name = (data.get("ngo_name") or "").strip()
    registration_number = (data.get("registration_number") or "").strip().upper()
    contact_person = (data.get("contact_person") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip().lower()
    address = (data.get("address") or "").strip()
    city = (data.get("city") or "Kolkata").strip()
    service_areas = (data.get("service_areas") or "Kolkata Metropolitan Area").strip()
    
    if not ngo_name or not registration_number or not contact_person:
        return jsonify({
            "success": False, 
            "error": "NGO name, official registration number, and contact person are required."
        }), 400
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    existing = query_db("SELECT id, verification_status FROM ngo_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    
    # Check registration number uniqueness against other NGOs
    dup_reg = query_db(
        "SELECT id FROM ngo_profiles WHERE registration_number = ? AND user_id != ?",
        (registration_number, user_id),
        one=True,
        db=conn
    )
    if dup_reg:
        return jsonify({
            "success": False,
            "error": f"Registration number '{registration_number}' is already registered with another organization."
        }), 409
        
    if existing:
        execute_db(
            """UPDATE ngo_profiles
               SET ngo_name = ?,
                   registration_number = ?,
                   contact_person = ?,
                   phone = ?,
                   email = ?,
                   address = ?,
                   city = ?,
                   service_areas = ?,
                   updated_at = ?
               WHERE user_id = ?""",
            (ngo_name, registration_number, contact_person, phone, email, address, city, service_areas, now, user_id),
            db=conn
        )
        msg = "NGO profile updated successfully."
    else:
        execute_db(
            """INSERT INTO ngo_profiles
               (user_id, ngo_name, registration_number, contact_person, phone, email, address, city, service_areas, verification_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)""",
            (user_id, ngo_name, registration_number, contact_person, phone, email, address, city, service_areas, now, now),
            db=conn
        )
        # Ensure user role is updated to ngo if not already
        execute_db("UPDATE users SET role = 'ngo', updated_at = ? WHERE id = ?", (now, user_id), db=conn)
        session["role"] = "ngo"
        msg = "NGO profile created successfully. Account submitted for administrative verification."
        
    profile = query_db("SELECT * FROM ngo_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    return jsonify({
        "success": True,
        "message": msg,
        "profile": profile
    }), 200

@ngo_bp.route("/api/ngo/donors", methods=["GET"])
@role_required("ngo", "admin")
def search_eligible_donors_for_ngo():
    """
    Search and filter eligible donors for registered NGOs.
    Enforces privacy protection: Donor phone and email are masked unless consent is granted.
    Excludes blocked accounts.
    """
    user_id = session["user_id"]
    conn = get_db()
    
    # Check NGO profile and verification status
    ngo_prof = query_db("SELECT * FROM ngo_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    is_verified = bool(ngo_prof and ngo_prof.get("verification_status") == "VERIFIED")
    
    # Query parameters
    blood_group = (request.args.get("blood_group") or "").strip().upper()
    city = (request.args.get("city") or "").strip()
    availability = (request.args.get("availability") or "").strip().upper()
    sort_by = (request.args.get("sort") or "best_match").strip().lower()
    
    # Fetch all candidate donors with user information
    sql = """
        SELECT dp.id AS donor_id, dp.user_id, dp.blood_group, dp.location, dp.availability,
               dp.maximum_travel_distance, dp.profile_status, dp.last_verified_date,
               u.full_name AS name, u.phone AS raw_phone, u.email AS raw_email,
               (SELECT COUNT(*) FROM donation_records WHERE donor_id = dp.user_id) AS total_donations,
               (SELECT MAX(donation_date) FROM donation_records WHERE donor_id = dp.user_id) AS last_donation_date,
               (SELECT COUNT(*) FROM donor_request_responses WHERE donor_id = dp.user_id AND status = 'ACCEPTED') AS accepted_responses,
               (SELECT COUNT(*) FROM donor_request_responses WHERE donor_id = dp.user_id) AS total_responses
        FROM donor_profiles dp
        JOIN users u ON dp.user_id = u.id
        WHERE dp.profile_status = 'ACTIVE'
    """
    params = []
    
    if blood_group and blood_group in VALID_BLOOD_GROUPS:
        sql += " AND dp.blood_group = ?"
        params.append(blood_group)
        
    if city:
        sql += " AND (dp.location LIKE ? OR u.city LIKE ?)"
        params.extend([f"%{city}%", f"%{city}%"])
        
    if availability and availability != "ALL":
        sql += " AND dp.availability = ?"
        params.append(availability)
        
    raw_donors = query_db(sql, params, db=conn) or []
    
    # Fetch blocked users for this NGO
    blocked_rows = query_db(
        """SELECT blocked_id FROM blocked_users WHERE blocker_id = ?
           UNION
           SELECT blocker_id FROM blocked_users WHERE blocked_id = ?""",
        (user_id, user_id),
        db=conn
    ) or []
    blocked_set = {r[0] for r in blocked_rows}
    
    # Fetch existing contact requests sent by this NGO to see if donor granted consent (ACCEPTED)
    requests_sent = query_db(
        "SELECT donor_id, status FROM ngo_contact_requests WHERE ngo_id = ?",
        (user_id,),
        db=conn
    ) or []
    consent_map = {r["donor_id"]: r["status"] for r in requests_sent}
    
    filtered_donors = []
    for d in raw_donors:
        donor_uid = d["user_id"]
        # Exclude blocked donors
        if donor_uid in blocked_set:
            continue
            
        req_status = consent_map.get(donor_uid)
        is_consent_granted = (req_status == "ACCEPTED")
        
        # Privacy masking
        if is_consent_granted:
            disp_phone = d["raw_phone"] or "+91 Confidential"
            disp_email = d["raw_email"] or ""
        else:
            disp_phone, disp_email = mask_contact(d["raw_phone"], d["raw_email"])
            
        # Recommendation Score computation
        # Proximity score (0-30), Availability score (0-25), Donation History (0-25), Response Reliability (0-20)
        tot_donations = d["total_donations"] or 0
        donation_score = min(25.0, tot_donations * 5.0)
        
        tot_resp = d["total_responses"] or 0
        acc_resp = d["accepted_responses"] or 0
        reliability_rate = round((acc_resp / tot_resp * 100) if tot_resp > 0 else 90.0, 1)
        reliability_score = round(reliability_rate * 0.2, 1)
        
        avail_score = 25.0 if d["availability"] == "24_HOURS" else 20.0
        prox_score = 25.0  # Base standard proximity
        
        recommendation_score = round(prox_score + avail_score + donation_score + reliability_score, 1)
        
        reasons = []
        if d["availability"] == "24_HOURS":
            reasons.append("24-Hour Emergency Availability")
        if tot_donations >= 3:
            reasons.append(f"Experienced Donor ({tot_donations} past donations)")
        if reliability_rate >= 80:
            reasons.append(f"High Reliability ({reliability_rate}% response rate)")
        if not reasons:
            reasons.append("Verified Active Donor")
            
        filtered_donors.append({
            "donor_id": d["donor_id"],
            "user_id": donor_uid,
            "name": d["name"],
            "blood_group": d["blood_group"],
            "location": d["location"] or "Kolkata",
            "availability": d["availability"],
            "total_donations": tot_donations,
            "last_donation_date": d["last_donation_date"] or "Eligible",
            "response_reliability": reliability_rate,
            "recommendation_score": recommendation_score,
            "recommendation_reasons": reasons,
            "phone": disp_phone,
            "email": disp_email,
            "is_contact_revealed": is_consent_granted,
            "contact_request_status": req_status or "NONE"
        })
        
    # Sorting
    if sort_by == "compatibility":
        filtered_donors.sort(key=lambda x: x["blood_group"])
    elif sort_by == "donation_history":
        filtered_donors.sort(key=lambda x: x["total_donations"], reverse=True)
    elif sort_by == "reliability":
        filtered_donors.sort(key=lambda x: x["response_reliability"], reverse=True)
    elif sort_by == "availability":
        filtered_donors.sort(key=lambda x: x["availability"] == "24_HOURS", reverse=True)
    else:  # best_match
        filtered_donors.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
    return jsonify({
        "success": True,
        "is_ngo_verified": is_verified,
        "verification_status": ngo_prof.get("verification_status") if ngo_prof else "UNREGISTERED",
        "total_donors": len(filtered_donors),
        "donors": filtered_donors
    }), 200

@ngo_bp.route("/api/ngo/contact-requests", methods=["POST"])
@ngo_bp.route("/api/ngo/contact-request", methods=["POST"])
@role_required("ngo", "admin")
def send_ngo_contact_request():
    """Send an outreach contact request to an eligible donor."""
    ngo_user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    # 1. Verification check: unverified NGOs cannot send requests
    ngo_prof = query_db("SELECT * FROM ngo_profiles WHERE user_id = ?", (ngo_user_id,), one=True, db=conn)
    if not ngo_prof or ngo_prof.get("verification_status") != "VERIFIED":
        return jsonify({
            "success": False,
            "error": "Administrative verification required. Your NGO account is currently PENDING approval."
        }), 403
        
    donor_id_raw = data.get("donor_id")
    blood_group = (data.get("required_blood_group") or "O+").strip().upper()
    message = (data.get("message") or f"Emergency outreach from {ngo_prof['ngo_name']} for blood donation support.").strip()
    
    if not donor_id_raw:
        return jsonify({"success": False, "error": "donor_id is required."}), 400
        
    # Find donor user id
    donor_user = query_db(
        "SELECT u.id, u.full_name, dp.blood_group FROM users u JOIN donor_profiles dp ON u.id = dp.user_id WHERE u.id = ? OR dp.id = ?",
        (donor_id_raw, donor_id_raw),
        one=True,
        db=conn
    )
    if not donor_user:
        return jsonify({"success": False, "error": "Donor not found."}), 404
        
    donor_uid = donor_user["id"]
    
    # Check for blocking
    is_blocked = query_db(
        """SELECT id FROM blocked_users 
           WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)""",
        (ngo_user_id, donor_uid, donor_uid, ngo_user_id),
        one=True,
        db=conn
    )
    if is_blocked:
        return jsonify({"success": False, "error": "Cannot contact this donor due to account privacy settings."}), 403
        
    # Check for duplicate pending or accepted request
    existing = query_db(
        "SELECT id, status FROM ngo_contact_requests WHERE ngo_id = ? AND donor_id = ? AND required_blood_group = ?",
        (ngo_user_id, donor_uid, blood_group),
        one=True,
        db=conn
    )
    if existing:
        return jsonify({
            "success": False,
            "error": f"A contact request with blood group {blood_group} has already been submitted (status: {existing['status']})."
        }), 409
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    req_id, _ = execute_db(
        """INSERT INTO ngo_contact_requests
           (ngo_id, donor_id, required_blood_group, message, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'PENDING', ?, ?)""",
        (ngo_user_id, donor_uid, blood_group, message, now, now),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (ngo_user_id, "NGO_CONTACT_REQUEST_SENT", f"NGO {ngo_prof['ngo_name']} contacted donor {donor_user['full_name']}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": f"Contact request sent to {donor_user['full_name']}. Direct contact information will be released upon donor consent.",
        "request_id": req_id,
        "status": "PENDING"
    }), 201

@ngo_bp.route("/api/ngo/contact-requests", methods=["GET"])
@role_required("ngo", "admin")
def list_ngo_contact_requests():
    """List contact requests sent by the authenticated NGO."""
    ngo_user_id = session["user_id"]
    conn = get_db()
    
    requests = query_db(
        """SELECT ncr.*, u.full_name AS donor_name, u.phone AS raw_phone, u.email AS raw_email,
                  dp.location AS donor_location, dp.blood_group AS donor_blood_group
           FROM ngo_contact_requests ncr
           JOIN users u ON ncr.donor_id = u.id
           JOIN donor_profiles dp ON u.id = dp.user_id
           WHERE ncr.ngo_id = ?
           ORDER BY ncr.created_at DESC""",
        (ngo_user_id,),
        db=conn
    ) or []
    
    sanitized = []
    for r in requests:
        status = r["status"]
        if status == "ACCEPTED":
            phone = r["raw_phone"] or "+91 Confidential"
            email = r["raw_email"] or ""
            is_revealed = True
        else:
            phone, email = mask_contact(r["raw_phone"], r["raw_email"])
            is_revealed = False
            
        sanitized.append({
            "id": r["id"],
            "donor_id": r["donor_id"],
            "donor_name": r["donor_name"],
            "donor_blood_group": r["donor_blood_group"],
            "required_blood_group": r["required_blood_group"],
            "donor_location": r["donor_location"],
            "message": r["message"],
            "status": status,
            "created_at": r["created_at"],
            "response_time": r["response_time"],
            "phone": phone,
            "email": email,
            "is_contact_revealed": is_revealed
        })
        
    return jsonify({"success": True, "contact_requests": sanitized}), 200

@ngo_bp.route("/api/donor/ngo-requests", methods=["GET"])
@login_required
def list_donor_incoming_ngo_requests():
    """List incoming NGO contact requests for a donor."""
    donor_user_id = session["user_id"]
    conn = get_db()
    
    requests = query_db(
        """SELECT ncr.*, np.ngo_name, np.contact_person, np.phone AS ngo_phone, np.email AS ngo_email, np.city AS ngo_city
           FROM ngo_contact_requests ncr
           JOIN ngo_profiles np ON ncr.ngo_id = np.user_id
           WHERE ncr.donor_id = ?
           ORDER BY 
               CASE ncr.status WHEN 'PENDING' THEN 1 ELSE 2 END,
               ncr.created_at DESC""",
        (donor_user_id,),
        db=conn
    ) or []
    
    return jsonify({"success": True, "requests": requests}), 200

@ngo_bp.route("/api/donor/ngo-requests/<int:request_id>/accept", methods=["POST"])
@login_required
def donor_accept_ngo_request(request_id):
    """Donor grants consent to share contact information with the NGO."""
    donor_user_id = session["user_id"]
    conn = get_db()
    
    req = query_db("SELECT * FROM ngo_contact_requests WHERE id = ? AND donor_id = ?", (request_id, donor_user_id), one=True, db=conn)
    if not req:
        return jsonify({"success": False, "error": "Request not found or unauthorized."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        "UPDATE ngo_contact_requests SET status = 'ACCEPTED', response_time = ?, updated_at = ? WHERE id = ?",
        (now, now, request_id),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (donor_user_id, "NGO_REQUEST_ACCEPTED", f"Donor consented to NGO contact request #{request_id}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": "Consent granted. The NGO has been provided with your verified contact information.",
        "status": "ACCEPTED"
    }), 200

@ngo_bp.route("/api/donor/ngo-requests/<int:request_id>/decline", methods=["POST"])
@login_required
def donor_decline_ngo_request(request_id):
    """Donor declines contact request from NGO."""
    donor_user_id = session["user_id"]
    conn = get_db()
    
    req = query_db("SELECT * FROM ngo_contact_requests WHERE id = ? AND donor_id = ?", (request_id, donor_user_id), one=True, db=conn)
    if not req:
        return jsonify({"success": False, "error": "Request not found or unauthorized."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        "UPDATE ngo_contact_requests SET status = 'DECLINED', response_time = ?, updated_at = ? WHERE id = ?",
        (now, now, request_id),
        db=conn
    )
    
    return jsonify({"success": True, "message": "NGO contact request declined.", "status": "DECLINED"}), 200

@ngo_bp.route("/api/ngo/contact-requests/<int:request_id>/complete", methods=["POST"])
@login_required
def mark_ngo_request_completed(request_id):
    """NGO marks contact request as completed."""
    ngo_user_id = session["user_id"]
    conn = get_db()
    
    req = query_db("SELECT * FROM ngo_contact_requests WHERE id = ? AND ngo_id = ?", (request_id, ngo_user_id), one=True, db=conn)
    if not req:
        return jsonify({"success": False, "error": "Request not found or unauthorized."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db("UPDATE ngo_contact_requests SET status = 'COMPLETED', updated_at = ? WHERE id = ?", (now, request_id), db=conn)
    return jsonify({"success": True, "message": "Request marked as completed.", "status": "COMPLETED"}), 200

@ngo_bp.route("/api/admin/ngos", methods=["GET"])
@role_required("admin")
def list_all_ngos_admin():
    """Admin lists all registered NGOs for verification."""
    conn = get_db()
    ngos = query_db(
        """SELECT np.*, u.full_name AS account_name, u.email AS account_email
           FROM ngo_profiles np
           JOIN users u ON np.user_id = u.id
           ORDER BY np.created_at DESC""",
        db=conn
    ) or []
    return jsonify({"success": True, "ngos": ngos}), 200

@ngo_bp.route("/api/admin/ngos/<int:profile_id>/verify", methods=["POST"])
@role_required("admin")
def verify_ngo_admin(profile_id):
    """Admin approves or rejects an NGO verification status."""
    data = request.get_json(silent=True) or request.form.to_dict()
    status = (data.get("status") or "VERIFIED").strip().upper()
    
    if status not in ("VERIFIED", "REJECTED", "PENDING"):
        return jsonify({"success": False, "error": "Invalid verification status."}), 400
        
    conn = get_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db("UPDATE ngo_profiles SET verification_status = ?, updated_at = ? WHERE id = ?", (status, now, profile_id), db=conn)
    
    return jsonify({
        "success": True,
        "message": f"NGO verification status set to {status}.",
        "verification_status": status
    }), 200

# ── PATIENT TO NGO WORKFLOW ENDPOINTS ─────────────────────────────────────

@ngo_bp.route("/api/ngo/patient-requests", methods=["GET"])
@role_required("ngo", "admin")
def list_incoming_patient_requests():
    """NGO views all blood requirement requests sent by hospital patients."""
    ngo_user_id = session["user_id"]
    conn = get_db()
    
    requests = query_db(
        """SELECT pnr.*, u.email AS patient_account_email
           FROM patient_ngo_requests pnr
           JOIN users u ON pnr.patient_id = u.id
           WHERE pnr.ngo_id = ?
           ORDER BY 
               CASE pnr.status WHEN 'PENDING' THEN 1 WHEN 'ACCEPTED' THEN 2 ELSE 3 END,
               pnr.created_at DESC""",
        (ngo_user_id,),
        db=conn
    ) or []
    
    return jsonify({"success": True, "requests": requests, "total_requests": len(requests)}), 200

@ngo_bp.route("/api/ngo/patient-requests/<int:req_id>/accept", methods=["POST"])
@role_required("ngo", "admin")
def accept_patient_request(req_id):
    """
    NGO accepts the patient's request and dispatches a response message
    (e.g. units prepared at blood bank, coordinator contact, or dispatch instructions).
    """
    ngo_user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    ngo_prof = query_db("SELECT * FROM ngo_profiles WHERE user_id = ?", (ngo_user_id,), one=True, db=conn)
    ngo_name = ngo_prof["ngo_name"] if ngo_prof else "Authorized NGO Blood Bank"
    
    default_msg = f"Units reserved at {ngo_name}. Please present your hospital requisition to our dispatch desk or contact coordinator at {ngo_prof['phone'] if ngo_prof else '+91 33 2222 0000'}."
    response_msg = (data.get("message") or default_msg).strip()
    
    req = query_db("SELECT * FROM patient_ngo_requests WHERE id = ? AND ngo_id = ?", (req_id, ngo_user_id), one=True, db=conn)
    if not req:
        return jsonify({"success": False, "error": "Request not found or unauthorized."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        """UPDATE patient_ngo_requests 
           SET status = 'ACCEPTED', ngo_response_message = ?, responded_at = ?, updated_at = ?
           WHERE id = ?""",
        (response_msg, now, now, req_id),
        db=conn
    )
    
    # Audit log
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (ngo_user_id, "NGO_ACCEPTED_PATIENT_REQUEST", f"{ngo_name} accepted blood request #{req_id} for {req['patient_name']}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": f"Blood request accepted! Dispatch message sent to patient {req['patient_name']}.",
        "status": "ACCEPTED",
        "response_message": response_msg
    }), 200

@ngo_bp.route("/api/ngo/patient-requests/<int:req_id>/decline", methods=["POST"])
@role_required("ngo", "admin")
def decline_patient_request(req_id):
    """NGO declines patient request due to stock or logistics constraints."""
    ngo_user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    reason = (data.get("message") or "Currently unavailable due to emergency inventory constraints.").strip()
    req = query_db("SELECT * FROM patient_ngo_requests WHERE id = ? AND ngo_id = ?", (req_id, ngo_user_id), one=True, db=conn)
    if not req:
        return jsonify({"success": False, "error": "Request not found or unauthorized."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        """UPDATE patient_ngo_requests 
           SET status = 'DECLINED', ngo_response_message = ?, responded_at = ?, updated_at = ?
           WHERE id = ?""",
        (reason, now, now, req_id),
        db=conn
    )
    
    return jsonify({"success": True, "message": "Request declined.", "status": "DECLINED"}), 200

@ngo_bp.route("/api/ngo/patient-requests/<int:req_id>/fulfill", methods=["POST"])
@role_required("ngo", "admin")
def fulfill_patient_request(req_id):
    """NGO marks blood handover as completed and fulfilled."""
    ngo_user_id = session["user_id"]
    conn = get_db()
    
    req = query_db("SELECT * FROM patient_ngo_requests WHERE id = ? AND ngo_id = ?", (req_id, ngo_user_id), one=True, db=conn)
    if not req:
        return jsonify({"success": False, "error": "Request not found or unauthorized."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db("UPDATE patient_ngo_requests SET status = 'FULFILLED', updated_at = ? WHERE id = ?", (now, req_id), db=conn)
    
    return jsonify({"success": True, "message": "Blood requirement fulfilled successfully.", "status": "FULFILLED"}), 200
