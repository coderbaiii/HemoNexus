"""
HEMONEXAS — Smart Blood Donor Management and Requirement-Based Matching System.
Root application entrypoint.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
from flask import Flask, jsonify, request, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash

from backend.config import Config
from backend.database import get_db, close_db, query_db, execute_db
from backend.init_db import init_database
from backend.app import create_app, app

__all__ = [
    "app",
    "create_app",
    "get_db",
    "close_db",
    "query_db",
    "execute_db",
    "generate_password_hash",
    "check_password_hash",
    "init_database",
    "Config"
]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
