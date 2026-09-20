import re
import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from backend.database import get_db, query_db, execute_db

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$"
VALID_ROLES = ("donor", "patient")

def login_required(f):
    """Decorator ensuring the user is logged into the session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator ensuring the logged in user has one of the allowed roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"success": False, "error": "Authentication required. Please log in."}), 401
            user_role = session.get("role")
            if user_role not in allowed_roles:
                return jsonify({"success": False, "error": "Forbidden: Insufficient privileges for this operation."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_user(user_dict):
    """Remove sensitive authentication fields like password hashes."""
    if not user_dict:
        return None
    safe = dict(user_dict)
    safe.pop("password_hash", None)
    safe.pop("password", None)
    return safe

@auth_bp.route("/api/register", methods=["POST"])
def register():
    """
    User registration endpoint.
    Accepts: full_name, email, password, role ('donor' or 'patient').
    Optional donor fields: blood_group, phone, location, latitude, longitude, availability, maximum_travel_distance.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().lower()
    
    # 1. Required field validation
    if not full_name or not email or not password or not role:
        return jsonify({"success": False, "error": "Full name, email, password, and role are required."}), 400
        
    # 2. Email format validation
    if not re.match(EMAIL_REGEX, email):
        return jsonify({"success": False, "error": "Invalid email address format."}), 400
        
    # 3. Password length check
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400
        
    # 4. Role validation: Users must NOT be able to self-register as admin
    if role not in VALID_ROLES:
        return jsonify({"success": False, "error": f"Invalid role '{role}'. Self-registration is only allowed for 'donor' or 'patient'."}), 400

    conn = get_db()
    
    # 5. Duplicate email check
    existing = query_db("SELECT id FROM users WHERE email = ?", (email,), one=True, db=conn)
    if existing:
        return jsonify({"success": False, "error": "An account with this email address already exists."}), 409
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    hashed = generate_password_hash(password)
    
    # Insert user
    user_id, _ = execute_db(
        "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (full_name, email, hashed, role, now, now),
        db=conn
    )
    
    # Create role-specific profile
    if role == "donor":
        blood_group = data.get("blood_group", "O+")
        phone = data.get("phone", "")
        location = data.get("location", "Not specified")
        lat = data.get("latitude")
        lon = data.get("longitude")
        avail = data.get("availability", "24_HOURS")
        max_dist = float(data.get("maximum_travel_distance") or 15.0)
        
        # Calculate 6-month verification dates
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        next_due = (now_dt + datetime.timedelta(days=Config.VERIFICATION_INTERVAL_DAYS)).isoformat()
        
        execute_db(
            """INSERT INTO donor_profiles 
               (user_id, blood_group, phone, location, latitude, longitude, availability, maximum_travel_distance, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?)""",
            (user_id, blood_group, phone, location, lat, lon, avail, max_dist, now, next_due, now, now),
            db=conn
        )
    elif role == "patient":
        phone = data.get("phone", "")
        location = data.get("location", "")
        lat = data.get("latitude")
        lon = data.get("longitude")
        execute_db(
            "INSERT INTO patient_profiles (user_id, phone, location, latitude, longitude, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, phone, location, lat, lon, now, now),
            db=conn
        )

    # Log action
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (user_id, "USER_REGISTERED", f"User registered with role {role}"),
        db=conn
    )
    
    # Auto log-in to session
    session.clear()
    session["user_id"] = user_id
    session["user_name"] = full_name
    session["user_email"] = email
    session["role"] = role
    
    return jsonify({
        "success": True,
        "message": f"Registration successful. Welcome to HEMONEXAS, {full_name}!",
        "user": {
            "id": user_id,
            "full_name": full_name,
            "email": email,
            "role": role
        }
    }), 201

@auth_bp.route("/api/login", methods=["POST"])
def login():
    """
    User login endpoint. Authenticates with email and password.
    Sets session cookies upon successful verification.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    
    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400
        
    conn = get_db()
    user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True, db=conn)
    
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401
        
    # Set Flask session
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]
    session["user_email"] = user["email"]
    session["role"] = user["role"]
    
    safe_user = sanitize_user(user)
    
    # Fetch profile details if present
    profile = None
    if user["role"] == "donor":
        profile = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user["id"],), one=True, db=conn)
    elif user["role"] == "patient":
        profile = query_db("SELECT * FROM patient_profiles WHERE user_id = ?", (user["id"],), one=True, db=conn)
        
    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": safe_user,
        "profile": profile
    }), 200

@auth_bp.route("/api/logout", methods=["POST", "GET"])
def logout():
    """Logs out the user and clears session state."""
    session.clear()
    return jsonify({"success": True, "message": "Successfully logged out."}), 200

@auth_bp.route("/api/me", methods=["GET"])
def get_current_user():
    """Returns the currently authenticated user and profile information."""
    if "user_id" not in session:
        return jsonify({"success": False, "user": None, "message": "No active session."}), 200
        
    user_id = session["user_id"]
    conn = get_db()
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True, db=conn)
    
    if not user:
        session.clear()
        return jsonify({"success": False, "user": None, "message": "User not found."}), 200
        
    safe_user = sanitize_user(user)
    profile = None
    if user["role"] == "donor":
        profile = query_db("SELECT * FROM donor_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
    elif user["role"] == "patient":
        profile = query_db("SELECT * FROM patient_profiles WHERE user_id = ?", (user_id,), one=True, db=conn)
        
    return jsonify({
        "success": True,
        "user": safe_user,
        "profile": profile
    }), 200

@auth_bp.route("/api/users", methods=["GET"])
@role_required("admin")
def list_users():
    """Admin-only endpoint to list all registered users."""
    conn = get_db()
    users = query_db("SELECT id, full_name, email, role, created_at, updated_at FROM users ORDER BY id ASC", db=conn)
    return jsonify({"success": True, "users": users}), 200
