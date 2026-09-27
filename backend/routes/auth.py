"""
Bridge to root routes.auth
"""
from routes.auth import auth_bp, login_required, role_required, sanitize_user

__all__ = ["auth_bp", "login_required", "role_required", "sanitize_user"]
