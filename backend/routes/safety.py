import datetime
from flask import Blueprint, request, jsonify, session
from backend.routes.auth import login_required
from backend.database import get_db, query_db, execute_db

safety_bp = Blueprint("safety", __name__)

@safety_bp.route("/api/blocked-users", methods=["GET"])
@login_required
def list_blocked_users():
    """Retrieve all users blocked by the authenticated user."""
    user_id = session["user_id"]
    conn = get_db()
    
    blocked = query_db(
        """SELECT b.id, b.blocker_id, b.blocked_id, b.reason, b.created_at,
                  u.full_name AS blocked_name, u.email AS blocked_email, u.role AS blocked_role
           FROM blocked_users b
           JOIN users u ON b.blocked_id = u.id
           WHERE b.blocker_id = ?
           ORDER BY b.created_at DESC""",
        (user_id,),
        db=conn
    ) or []
    
    return jsonify({
        "success": True,
        "blocked_users": blocked,
        "count": len(blocked)
    }), 200

@safety_bp.route("/api/blocked-users", methods=["POST"])
@login_required
def block_user():
    """
    Block a user from contacting or appearing in recommendations.
    Enforces safety rules: cannot block self, cannot block platform administrators.
    """
    blocker_id = session["user_id"]
    data = request.get_json(silent=True) or request.form.to_dict()
    conn = get_db()
    
    blocked_id_raw = data.get("blocked_id")
    reason = (data.get("reason") or "Unwanted contact or harassment").strip()
    
    if not blocked_id_raw:
        return jsonify({"success": False, "error": "blocked_id is required."}), 400
        
    try:
        blocked_id = int(blocked_id_raw)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid blocked_id format."}), 400
        
    # Safety Check 1: Cannot block self
    if blocker_id == blocked_id:
        return jsonify({"success": False, "error": "Self-blocking is prohibited."}), 400
        
    target_user = query_db("SELECT id, full_name, email, role FROM users WHERE id = ?", (blocked_id,), one=True, db=conn)
    if not target_user:
        return jsonify({"success": False, "error": "User to block does not exist."}), 404
        
    # Safety Check 2: Cannot block administrator
    if target_user["role"].lower() == "admin":
        return jsonify({"success": False, "error": "Platform safety policy: Administrative accounts cannot be blocked."}), 403
        
    # Check if already blocked
    existing = query_db(
        "SELECT id FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?",
        (blocker_id, blocked_id),
        one=True,
        db=conn
    )
    if existing:
        return jsonify({
            "success": True,
            "message": f"User '{target_user['full_name']}' is already blocked.",
            "blocked_id": blocked_id
        }), 200
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record_id, _ = execute_db(
        """INSERT INTO blocked_users (blocker_id, blocked_id, reason, created_at)
           VALUES (?, ?, ?, ?)""",
        (blocker_id, blocked_id, reason, now),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (blocker_id, "USER_BLOCKED", f"Blocked user #{blocked_id} ({target_user['full_name']})"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": f"Account '{target_user['full_name']}' has been blocked successfully.",
        "record_id": record_id,
        "blocked_user": {
            "id": target_user["id"],
            "full_name": target_user["full_name"],
            "role": target_user["role"]
        }
    }), 201

@safety_bp.route("/api/blocked-users/<int:blocked_id>", methods=["DELETE"])
@login_required
def unblock_user(blocked_id):
    """Unblock a previously blocked user account."""
    blocker_id = session["user_id"]
    conn = get_db()
    
    existing = query_db(
        """SELECT b.id, u.full_name 
           FROM blocked_users b 
           JOIN users u ON b.blocked_id = u.id 
           WHERE b.blocker_id = ? AND b.blocked_id = ?""",
        (blocker_id, blocked_id),
        one=True,
        db=conn
    )
    if not existing:
        return jsonify({"success": False, "error": "Blocked account record not found."}), 404
        
    execute_db(
        "DELETE FROM blocked_users WHERE blocker_id = ? AND blocked_id = ?",
        (blocker_id, blocked_id),
        db=conn
    )
    
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (blocker_id, "USER_UNBLOCKED", f"Unblocked user #{blocked_id} ({existing['full_name']})"),
        db=conn
    )
    
    return jsonify({
        "success": True,
        "message": f"Account '{existing['full_name']}' has been unblocked successfully.",
        "unblocked_id": blocked_id
    }), 200
