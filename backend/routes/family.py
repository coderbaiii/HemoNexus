import datetime
from flask import Blueprint, request, jsonify, session
from backend.routes.auth import login_required
from backend.database import get_db, query_db, execute_db

family_bp = Blueprint("family", __name__)

VALID_RELATIONSHIPS = ("Father", "Mother", "Brother", "Sister", "Spouse", "Child", "Other")
VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")

@family_bp.route("/api/family-members", methods=["GET"])
@login_required
def list_family_members():
    """List all family members for the authenticated user, attaching any active blood requirements."""
    user_id = session["user_id"]
    conn = get_db()
    
    members = query_db(
        """SELECT f.*,
                  (SELECT COUNT(*) 
                   FROM blood_requests br 
                   WHERE br.patient_id = f.user_id 
                     AND br.required_blood_group = f.blood_group
                     AND br.request_status IN ('OPEN', 'MATCHING')) AS has_active_request
           FROM family_members f
           WHERE f.user_id = ?
           ORDER BY f.created_at ASC""",
        (user_id,),
        db=conn
    ) or []
    
    return jsonify({
        "success": True,
        "family_members": members,
        "count": len(members)
    }), 200

@family_bp.route("/api/family-members", methods=["POST"])
@login_required
def add_family_member():
    """Add a new family member linked to the current user."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    full_name = (data.get("full_name") or "").strip()
    relationship = (data.get("relationship") or "").strip().capitalize()
    blood_group = (data.get("blood_group") or "").strip().upper()
    age_raw = data.get("age")
    contact_number = (data.get("contact_number") or "").strip() or None
    medical_notes = (data.get("medical_notes") or "").strip() or None
    
    if not full_name:
        return jsonify({"success": False, "error": "Family member full name is required."}), 400
        
    if relationship not in VALID_RELATIONSHIPS:
        return jsonify({
            "success": False, 
            "error": f"Invalid relationship '{relationship}'. Valid options: {', '.join(VALID_RELATIONSHIPS)}"
        }), 400
        
    if blood_group not in VALID_BLOOD_GROUPS:
        return jsonify({
            "success": False,
            "error": f"Invalid blood group '{blood_group}'. Valid options: {', '.join(VALID_BLOOD_GROUPS)}"
        }), 400
        
    age = None
    if age_raw is not None and str(age_raw).strip() != "":
        try:
            age = int(age_raw)
            if age <= 0 or age >= 130:
                return jsonify({"success": False, "error": "Age must be between 1 and 129."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Age must be a valid integer."}), 400
            
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    member_id, _ = execute_db(
        """INSERT INTO family_members 
           (user_id, full_name, relationship, blood_group, age, contact_number, medical_notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, full_name, relationship, blood_group, age, contact_number, medical_notes, now, now),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, "FAMILY_MEMBER_ADDED", f"Added family member {full_name} ({relationship}, {blood_group})"),
        db=conn
    )
    
    new_member = query_db("SELECT * FROM family_members WHERE id = ?", (member_id,), one=True, db=conn)
    return jsonify({
        "success": True,
        "message": f"Family member '{full_name}' added successfully.",
        "family_member": new_member
    }), 201

@family_bp.route("/api/family-members/<int:member_id>", methods=["GET"])
@login_required
def get_family_member(member_id):
    """Retrieve details for a specific family member."""
    user_id = session["user_id"]
    conn = get_db()
    
    member = query_db(
        "SELECT * FROM family_members WHERE id = ? AND user_id = ?",
        (member_id, user_id),
        one=True,
        db=conn
    )
    if not member:
        return jsonify({"success": False, "error": "Family member not found or access unauthorized."}), 404
        
    return jsonify({"success": True, "family_member": member}), 200

@family_bp.route("/api/family-members/<int:member_id>", methods=["PUT", "PATCH"])
@login_required
def update_family_member(member_id):
    """Update an existing family member."""
    user_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    existing = query_db(
        "SELECT * FROM family_members WHERE id = ? AND user_id = ?",
        (member_id, user_id),
        one=True,
        db=conn
    )
    if not existing:
        return jsonify({"success": False, "error": "Family member not found or access unauthorized."}), 404
        
    full_name = (data.get("full_name") or existing["full_name"]).strip()
    relationship = (data.get("relationship") or existing["relationship"]).strip().capitalize()
    blood_group = (data.get("blood_group") or existing["blood_group"]).strip().upper()
    
    if relationship not in VALID_RELATIONSHIPS:
        return jsonify({"success": False, "error": f"Invalid relationship '{relationship}'."}), 400
        
    if blood_group not in VALID_BLOOD_GROUPS:
        return jsonify({"success": False, "error": f"Invalid blood group '{blood_group}'."}), 400
        
    age = existing["age"]
    if "age" in data:
        age_raw = data.get("age")
        if age_raw is not None and str(age_raw).strip() != "":
            try:
                age = int(age_raw)
                if age <= 0 or age >= 130:
                    return jsonify({"success": False, "error": "Age must be between 1 and 129."}), 400
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "Age must be an integer."}), 400
        else:
            age = None
            
    contact_number = data.get("contact_number", existing["contact_number"])
    if contact_number is not None:
        contact_number = str(contact_number).strip() or None
        
    medical_notes = data.get("medical_notes", existing["medical_notes"])
    if medical_notes is not None:
        medical_notes = str(medical_notes).strip() or None
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    execute_db(
        """UPDATE family_members
           SET full_name = ?,
               relationship = ?,
               blood_group = ?,
               age = ?,
               contact_number = ?,
               medical_notes = ?,
               updated_at = ?
           WHERE id = ? AND user_id = ?""",
        (full_name, relationship, blood_group, age, contact_number, medical_notes, now, member_id, user_id),
        db=conn
    )
    
    updated = query_db("SELECT * FROM family_members WHERE id = ?", (member_id,), one=True, db=conn)
    return jsonify({
        "success": True,
        "message": f"Family member '{full_name}' updated successfully.",
        "family_member": updated
    }), 200

@family_bp.route("/api/family-members/<int:member_id>", methods=["DELETE"])
@login_required
def delete_family_member(member_id):
    """Delete a family member belonging to the user."""
    user_id = session["user_id"]
    conn = get_db()
    
    existing = query_db(
        "SELECT full_name FROM family_members WHERE id = ? AND user_id = ?",
        (member_id, user_id),
        one=True,
        db=conn
    )
    if not existing:
        return jsonify({"success": False, "error": "Family member not found or access unauthorized."}), 404
        
    execute_db(
        "DELETE FROM family_members WHERE id = ? AND user_id = ?",
        (member_id, user_id),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, "FAMILY_MEMBER_DELETED", f"Deleted family member {existing['full_name']}"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": f"Family member '{existing['full_name']}' deleted successfully."
    }), 200
