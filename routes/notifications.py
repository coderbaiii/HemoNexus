"""
HEMONEXAS In-App Notifications Blueprint
Provides endpoints to fetch and mark notifications read.
"""
from flask import Blueprint, jsonify, session
from database.db import get_db, query_db, execute_db
from models.notification import NotificationModel

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/api/notifications", methods=["GET"])
def get_user_notifications():
    """Returns in-app notifications for the logged in user."""
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Authentication required."}), 401
        
    user_id = session["user_id"]
    conn = get_db()
    notifs = NotificationModel.list_for_user(user_id, unread_only=False, db=conn)
    unread_count = sum(1 for n in notifs if n.get("is_read") == 0)
    
    return jsonify({
        "success": True,
        "unread_count": unread_count,
        "notifications": notifs
    }), 200

@notifications_bp.route("/api/notifications/read-all", methods=["POST"])
def mark_notifications_read():
    """Marks all notifications as read for current user."""
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Authentication required."}), 401
        
    user_id = session["user_id"]
    conn = get_db()
    NotificationModel.mark_all_read(user_id, db=conn)
    return jsonify({"success": True, "message": "All notifications marked as read."}), 200

@notifications_bp.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
def mark_single_read(notif_id):
    """Marks a single notification as read."""
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Authentication required."}), 401
        
    user_id = session["user_id"]
    conn = get_db()
    execute_db("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user_id), db=conn)
    return jsonify({"success": True, "message": "Notification marked as read."}), 200
