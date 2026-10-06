import re
import os
import random
import smtplib
from email.message import EmailMessage
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

def send_otp_email(recipient_email, otp_code, recipient_name="User"):
    """
    Sends a 6-digit OTP email using configured SMTP settings.
    Supports Gmail, Outlook, or custom SMTP server via environment variables:
    SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD.
    """
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    sender_email = os.environ.get("SMTP_EMAIL") or os.environ.get("MAIL_USERNAME")
    sender_password = os.environ.get("SMTP_PASSWORD") or os.environ.get("MAIL_PASSWORD")

    if not sender_email or not sender_password:
        return False, "SMTP credentials not configured."

    msg = EmailMessage()
    msg["Subject"] = "HemoNexus Security: Password Reset Verification Code"
    msg["From"] = f"HemoNexus Security <{sender_email}>"
    msg["To"] = recipient_email

    msg.set_content(f"""Hello {recipient_name},

Your HemoNexus password reset verification code is: {otp_code}

This code is valid for 10 minutes. If you did not request this, please ignore this email.

— Team HemoNexus
""")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
      <div style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <div style="text-align: center; margin-bottom: 24px;">
          <h2 style="color: #e11d48; margin: 0; font-size: 24px; font-weight: 800;">🩸 HemoNexus</h2>
          <p style="color: #64748b; font-size: 13px; margin: 4px 0 0 0;">Smart Blood Donor Network</p>
        </div>
        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 12px; color: #0f172a;">Password Reset Verification</h3>
        <p style="font-size: 14px; line-height: 1.5; color: #475569;">Hello <strong>{recipient_name}</strong>,</p>
        <p style="font-size: 14px; line-height: 1.5; color: #475569;">You recently requested to reset your account password. Enter the 6-digit verification code below to verify your identity:</p>
        <div style="text-align: center; margin: 24px 0;">
          <div style="display: inline-block; background: #fef2f2; border: 2px dashed #e11d48; padding: 12px 28px; font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #e11d48; border-radius: 8px;">
            {otp_code}
          </div>
        </div>
        <p style="font-size: 12px; color: #94a3b8; text-align: center;">This verification code will expire in <strong>10 minutes</strong>.</p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="font-size: 12px; color: #64748b; margin: 0;">If you did not request this password reset, please ignore this email or secure your account.</p>
      </div>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype="html")

    # 1. Try port 587 with STARTTLS
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=8) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True, "Email sent successfully."
    except Exception as e_starttls:
        # 2. Try port 465 with SSL
        try:
            with smtplib.SMTP_SSL(smtp_server, 465, timeout=8) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
            return True, "Email sent successfully via SSL."
        except Exception as e_ssl:
            return False, f"{str(e_starttls)}"

@auth_bp.route("/api/send-otp", methods=["POST"])
@auth_bp.route("/api/auth/send-otp", methods=["POST"])
def send_otp():
    """Generates and sends a 6-digit OTP verification code to registered email."""
    data = request.get_json(silent=True) or request.form.to_dict()
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"success": False, "error": "Email address is required."}), 400

    conn = get_db()
    # Check if user exists
    user = query_db("SELECT id, full_name, email FROM users WHERE email = ?", (email,), one=True, db=conn)
    if not user:
        return jsonify({"success": False, "error": f"No account found with email '{email}'."}), 404

    # Generate random 6-digit code
    otp = f"{random.randint(100000, 999999)}"
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = (now + datetime.timedelta(minutes=10)).isoformat()
    now_iso = now.isoformat()

    # Save to password_reset_tokens table (upsert)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            otp_code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    conn.commit()

    execute_db(
        """INSERT INTO password_reset_tokens (email, otp_code, expires_at, created_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(email) DO UPDATE SET otp_code=excluded.otp_code, expires_at=excluded.expires_at, created_at=excluded.created_at""",
        (email, otp, expires_at, now_iso),
        db=conn
    )

    # Attempt to send email
    sent, reason = send_otp_email(email, otp, recipient_name=user["full_name"])
    print(f"[HemoNexus Security] OTP generated for {email}. (Email sent: {sent}, status: {reason})")

    if not sent:
        # Check if failure is due to cloud host firewall blocking outbound SMTP (e.g. Render Free Tier)
        is_cloud_blocked = "unreachable" in reason.lower() or "101" in reason or "timed out" in reason.lower() or "errno 101" in reason.lower()
        if is_cloud_blocked:
            return jsonify({
                "success": True,
                "cloud_blocked": True,
                "dev_otp": otp,
                "message": f"Cloud Host Notice: Outbound SMTP port is firewalled on Render Free Tier. Verification Code: {otp}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Email dispatch failed: {reason}. Please check SMTP credentials."
            }), 503

    return jsonify({
        "success": True,
        "message": f"A 6-digit verification code has been dispatched to {email}. Please check your inbox (and spam folder)."
    }), 200

@auth_bp.route("/api/reset-password", methods=["POST"])
@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    """Self-service password reset with mandatory OTP verification."""
    data = request.get_json(silent=True) or request.form.to_dict()
    email = (data.get("email") or "").strip().lower()
    otp_provided = (data.get("otp") or "").strip()
    new_password = data.get("password") or data.get("new_password") or ""

    if not email:
        return jsonify({"success": False, "error": "Email is required."}), 400

    if not otp_provided:
        return jsonify({"success": False, "error": "6-digit verification code is required."}), 400

    if not new_password:
        return jsonify({"success": False, "error": "New password is required."}), 400

    if len(new_password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400

    conn = get_db()
    # 1. Verify user exists
    user = query_db("SELECT id, full_name, email FROM users WHERE email = ?", (email,), one=True, db=conn)
    if not user:
        return jsonify({"success": False, "error": f"No account found with email '{email}'."}), 404

    # 2. Check token in password_reset_tokens
    token_row = query_db("SELECT * FROM password_reset_tokens WHERE email = ?", (email,), one=True, db=conn)
    if not token_row:
        return jsonify({"success": False, "error": "No pending verification code found. Please click 'Send Verification Code'."}), 400

    # 3. Check expiration
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        exp_dt = datetime.datetime.fromisoformat(token_row["expires_at"].replace("Z", "+00:00"))
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=datetime.timezone.utc)
        if now > exp_dt:
            return jsonify({"success": False, "error": "Verification code has expired. Please request a new code."}), 400
    except Exception:
        pass

    # 4. Check OTP match
    if token_row["otp_code"].strip() != otp_provided:
        return jsonify({"success": False, "error": "Invalid verification code. Please check your email and try again."}), 400

    # 5. OTP is valid! Update password
    now_iso = now.isoformat()
    hashed = generate_password_hash(new_password)
    execute_db(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (hashed, now_iso, user["id"]),
        db=conn
    )

    # Delete used token
    execute_db("DELETE FROM password_reset_tokens WHERE email = ?", (email,), db=conn)

    # Audit log
    execute_db(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
        (user["id"], "PASSWORD_RESET_OTP_VERIFIED", f"Password reset verified via OTP for {user['email']}"),
        db=conn
    )

    return jsonify({
        "success": True,
        "message": f"Password for {user['full_name']} has been successfully updated! You can now sign in."
    }), 200


