"""
HEMONEXAS Notification Model
Manages in-app notifications and alerts.
"""
from database.db import query_db, execute_db

class NotificationModel:
    @staticmethod
    def create(user_id, title, message, notif_type="INFO", link=None, db=None):
        return execute_db(
            "INSERT INTO notifications (user_id, title, message, type, link) VALUES (?, ?, ?, ?, ?)",
            (user_id, title, message, notif_type, link),
            db=db
        )

    @staticmethod
    def list_for_user(user_id, unread_only=False, db=None):
        sql = "SELECT * FROM notifications WHERE user_id = ?"
        args = [user_id]
        if unread_only:
            sql += " AND is_read = 0"
        sql += " ORDER BY created_at DESC"
        return query_db(sql, args, db=db)

    @staticmethod
    def mark_all_read(user_id, db=None):
        return execute_db("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,), db=db)
