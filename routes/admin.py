"""
HEMONEXAS Administrator Blueprint
Provides system oversight, donor verification audits, donation completion logs,
and operational metrics.
"""
import datetime
from flask import Blueprint, request, jsonify
from routes.auth import role_required
from database.db import get_db, query_db, execute_db
from models.donor import DonorModel

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
    total_donations = query_db("SELECT COUNT(*) AS count FROM donation_records", one=True, db=conn)["count"]
    
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
            "accepted_responses": accepted_responses,
            "total_donation_records": total_donations
        }
    }), 200

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
    """List all registered patients and contact details."""
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
    requests_list = query_db(sql, db=conn)
    return jsonify({"success": True, "requests": requests_list}), 200

@admin_bp.route("/api/admin/donations", methods=["GET", "POST"])
@role_required("admin")
def manage_donations():
    """Admin records certified blood donation or views records."""
    conn = get_db()
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        donor_id = data.get("donor_id")
        patient_id = data.get("patient_id")
        center = data.get("blood_center_name", "Authorized Blood Bank")
        notes = data.get("verification_notes", "Clinical screening authorized by medical staff.")
        units = int(data.get("units_donated", 1))
        
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        rec_id, _ = execute_db(
            """INSERT INTO donation_records 
               (donor_id, patient_id, donation_date, blood_center_name, units_donated, verification_notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (donor_id, patient_id, now, center, units, notes, now),
            db=conn
        )
        return jsonify({"success": True, "message": "Donation record logged.", "record_id": rec_id}), 201
        
    records = query_db(
        """SELECT dr.*, u_d.full_name AS donor_name, u_p.full_name AS patient_name
           FROM donation_records dr
           JOIN users u_d ON dr.donor_id = u_d.id
           LEFT JOIN users u_p ON dr.patient_id = u_p.id
           ORDER BY dr.donation_date DESC""",
        db=conn
    )
    return jsonify({"success": True, "donations": records}), 200

@admin_bp.route("/api/admin/users", methods=["GET"])
@role_required("admin")
def list_admin_users():
    """Admin-only endpoint to list all registered users."""
    conn = get_db()
    users = query_db("SELECT id, full_name, email, role, created_at, updated_at FROM users ORDER BY id ASC", db=conn)
    return jsonify({"success": True, "users": users}), 200

@admin_bp.route("/api/admin/verify-check", methods=["POST"])
@admin_bp.route("/api/admin/verification/sweep", methods=["POST"])
@role_required("admin")
def run_verification_sweep():
    """Runs the 6-month verification cycle lifecycle check across all donors."""
    conn = get_db()
    total_donors = query_db("SELECT COUNT(*) AS count FROM donor_profiles", one=True, db=conn)["count"]
    updated_count = DonorModel.sweep_statuses(db=conn)
    return jsonify({
        "success": True,
        "message": f"Verification sweep completed. {updated_count} donor profile statuses updated according to 6-month lifecycle rules.",
        "details": {
            "evaluated": total_donors,
            "updated": updated_count
        }
    }), 200

@admin_bp.route("/api/admin/donors/<int:donor_id>/status", methods=["PATCH", "POST"])
@role_required("admin")
def override_donor_status(donor_id):
    """Admin manually overrides a donor's profile status."""
    data = request.get_json(silent=True) or request.form.to_dict()
    new_status = (data.get("status") or "").strip().upper()
    if new_status not in ("ACTIVE", "VERIFICATION_DUE", "INACTIVE"):
        return jsonify({"success": False, "error": f"Invalid status '{new_status}'."}), 400
        
    conn = get_db()
    donor = query_db("SELECT id FROM donor_profiles WHERE id = ?", (donor_id,), one=True, db=conn)
    if not donor:
        return jsonify({"success": False, "error": "Donor not found."}), 404
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    execute_db("UPDATE donor_profiles SET profile_status = ?, updated_at = ? WHERE id = ?", (new_status, now, donor_id), db=conn)
    return jsonify({"success": True, "new_status": new_status, "message": f"Status updated to {new_status}."}), 200

@admin_bp.route("/api/admin/logs", methods=["GET"])
@role_required("admin")
def get_audit_logs():
    """List recent audit logs for system traceability."""
    conn = get_db()
    logs = query_db(
        """SELECT l.*, u.full_name, u.email 
           FROM audit_logs l
           LEFT JOIN users u ON l.user_id = u.id
           ORDER BY l.created_at DESC
           LIMIT 50""",
        db=conn
    )
    return jsonify({"success": True, "logs": logs}), 200
