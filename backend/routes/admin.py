import datetime
from flask import Blueprint, request, jsonify, session
from backend.routes.auth import role_required
from backend.database import get_db, query_db, execute_db
from backend.services.verification_service import sweep_and_update_donor_statuses

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/api/admin/stats", methods=["GET"])
@role_required("admin")
def get_admin_stats():
    """Returns overview platform analytics and verification statistics."""
    conn = get_db()
    
    total_users = query_db("SELECT COUNT(*) AS count FROM users", one=True, db=conn)["count"]
    total_donors = query_db("SELECT COUNT(*) AS count FROM donor_profiles", one=True, db=conn)["count"]
    total_patients = query_db("SELECT COUNT(*) AS count FROM patient_profiles", one=True, db=conn)["count"]
    
    active_donors = query_db("SELECT COUNT(*) AS count FROM donor_profiles WHERE profile_status = 'ACTIVE'", one=True, db=conn)["count"]
    due_donors = query_db("SELECT COUNT(*) AS count FROM donor_profiles WHERE profile_status = 'VERIFICATION_DUE'", one=True, db=conn)["count"]
    inactive_donors = query_db("SELECT COUNT(*) AS count FROM donor_profiles WHERE profile_status = 'INACTIVE'", one=True, db=conn)["count"]
    
    total_requests = query_db("SELECT COUNT(*) AS count FROM blood_requests", one=True, db=conn)["count"]
    open_requests = query_db("SELECT COUNT(*) AS count FROM blood_requests WHERE request_status = 'OPEN'", one=True, db=conn)["count"]
    fulfilled_requests = query_db("SELECT COUNT(*) AS count FROM blood_requests WHERE request_status = 'FULFILLED'", one=True, db=conn)["count"]
    
    total_responses = query_db("SELECT COUNT(*) AS count FROM donor_request_responses", one=True, db=conn)["count"]
    accepted_responses = query_db("SELECT COUNT(*) AS count FROM donor_request_responses WHERE status = 'ACCEPTED'", one=True, db=conn)["count"]
    
    return jsonify({
        "success": True,
        "stats": {
            "total_users": total_users,
            "total_donors": total_donors,
            "total_patients": total_patients,
            "active_donors": active_donors,
            "verification_due_donors": due_donors,
            "inactive_donors": inactive_donors,
            "total_blood_requests": total_requests,
            "open_blood_requests": open_requests,
            "fulfilled_blood_requests": fulfilled_requests,
            "total_responses": total_responses,
            "accepted_responses": accepted_responses
        }
    }), 200

@admin_bp.route("/api/admin/users", methods=["GET"])
@role_required("admin")
def list_users():
    """List all registered users without exposing passwords."""
    conn = get_db()
    users = query_db("SELECT id, full_name, email, role, created_at, updated_at FROM users ORDER BY id DESC", db=conn)
    return jsonify({"success": True, "users": users}), 200

@admin_bp.route("/api/admin/donors", methods=["GET"])
@role_required("admin")
def list_donors():
    """List donors with optional status filtering (?status=ACTIVE|VERIFICATION_DUE|INACTIVE)."""
    status_filter = request.args.get("status")
    conn = get_db()
    
    sql = """
        SELECT d.*, u.full_name, u.email
        FROM donor_profiles d
        JOIN users u ON d.user_id = u.id
    """
    args = []
    if status_filter:
        sql += " WHERE d.profile_status = ?"
        args.append(status_filter.upper())
        
    sql += " ORDER BY d.id DESC"
    donors = query_db(sql, args, db=conn)
    return jsonify({"success": True, "donors": donors}), 200

@admin_bp.route("/api/admin/patients", methods=["GET"])
@role_required("admin")
def list_patients():
    """List all patients and profile information."""
    conn = get_db()
    sql = """
        SELECT p.*, u.full_name, u.email
        FROM patient_profiles p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.id DESC
    """
    patients = query_db(sql, db=conn)
    return jsonify({"success": True, "patients": patients}), 200

@admin_bp.route("/api/admin/blood-requests", methods=["GET"])
@role_required("admin")
def list_all_requests():
    """List all blood requests across the system."""
    conn = get_db()
    sql = """
        SELECT br.*, u.full_name AS patient_name, u.email AS patient_email
        FROM blood_requests br
        JOIN users u ON br.patient_id = u.id
        ORDER BY br.created_at DESC
    """
    requests = query_db(sql, db=conn)
    return jsonify({"success": True, "requests": requests}), 200

@admin_bp.route("/api/admin/responses", methods=["GET"])
@role_required("admin")
def list_all_responses():
    """List all donor request responses and communication."""
    conn = get_db()
    sql = """
        SELECT r.*,
               br.required_blood_group, br.hospital_name, br.urgency,
               patient.full_name AS patient_name,
               donor.full_name AS donor_name
        FROM donor_request_responses r
        JOIN blood_requests br ON r.blood_request_id = br.id
        JOIN users patient ON br.patient_id = patient.id
        JOIN users donor ON r.donor_id = donor.id
        ORDER BY r.created_at DESC
    """
    responses = query_db(sql, db=conn)
    return jsonify({"success": True, "responses": responses}), 200

@admin_bp.route("/api/admin/verify-check", methods=["POST"])
@role_required("admin")
def run_verification_sweep():
    """Administrator triggers system-wide six-month verification check."""
    conn = get_db()
    stats = sweep_and_update_donor_statuses(db=conn)
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (session["user_id"], "ADMIN_VERIFICATION_SWEEP", f"Evaluated {stats['evaluated']} donors; updated {stats['updated']} records."),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": f"Verification sweep completed: {stats['evaluated']} evaluated, {stats['updated']} statuses updated.",
        "details": stats
    }), 200

@admin_bp.route("/api/admin/donors/<int:donor_id>/status", methods=["PATCH", "PUT"])
@role_required("admin")
def manage_donor_status(donor_id):
    """Admin overrides donor profile status (ACTIVE, VERIFICATION_DUE, INACTIVE)."""
    data = request.get_json(silent=True) or request.form.to_dict()
    new_status = (data.get("status") or "").strip().upper()
    
    if new_status not in ("ACTIVE", "VERIFICATION_DUE", "INACTIVE"):
        return jsonify({"success": False, "error": "Invalid status. Allowed: ACTIVE, VERIFICATION_DUE, INACTIVE"}), 400
        
    conn = get_db()
    donor = query_db("SELECT id, user_id, profile_status FROM donor_profiles WHERE id = ?", (donor_id,), one=True, db=conn)
    if not donor:
        return jsonify({"success": False, "error": "Donor not found."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db(
        "UPDATE donor_profiles SET profile_status = ?, updated_at = ? WHERE id = ?",
        (new_status, now, donor_id),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (session["user_id"], "ADMIN_STATUS_OVERRIDE", f"Updated donor #{donor_id} status from {donor['profile_status']} to {new_status}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": f"Donor status updated to {new_status}.",
        "donor_id": donor_id,
        "new_status": new_status
    }), 200
