"""
HEMONEXAS Routes Package
"""
from routes.auth import auth_bp
from routes.donor import donor_bp
from routes.patient import patient_bp
from routes.admin import admin_bp
from routes.search import search_bp
from routes.notifications import notifications_bp
from routes.chatbot import chatbot_bp
from routes.web import web_bp

__all__ = [
    "auth_bp",
    "donor_bp",
    "patient_bp",
    "admin_bp",
    "search_bp",
    "notifications_bp",
    "chatbot_bp",
    "web_bp"
]
