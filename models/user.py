"""
HEMONEXAS User Model
Handles user accounts, password hashing, and role checks.
"""
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import query_db, execute_db

class UserModel:
    """Helper for user operations and authentication verification."""

    @staticmethod
    def get_by_id(user_id, db=None):
        return query_db("SELECT id, full_name, email, role, created_at, updated_at FROM users WHERE id = ?", (user_id,), one=True, db=db)

    @staticmethod
    def get_by_email(email, db=None):
        if not email:
            return None
        return query_db("SELECT * FROM users WHERE email = ?", (email.strip().lower(),), one=True, db=db)

    @staticmethod
    def create(full_name, email, password, role="patient", db=None):
        hashed = generate_password_hash(password)
        email_clean = email.strip().lower()
        user_id, _ = execute_db(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (full_name.strip(), email_clean, hashed, role.lower()),
            db=db
        )
        return user_id

    @staticmethod
    def verify_password(stored_hash, raw_password):
        if not stored_hash or not raw_password:
            return False
        return check_password_hash(stored_hash, raw_password)
