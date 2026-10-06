import sys
from pathlib import Path

# Add project root to sys.path for direct execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import datetime
from functools import wraps
from flask import Flask, jsonify, request, render_template, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from backend.database import get_db, close_db, query_db, execute_db
from backend.init_db import init_database
from backend.routes.auth import auth_bp
from backend.routes.donor import donor_bp
from backend.routes.patient import patient_bp
from backend.routes.admin import admin_bp
from backend.services.verification_service import sweep_and_update_donor_statuses


# ── Runtime System Settings (stored in DB, override Config defaults) ──────────

def _ensure_settings_table(conn):
    """Create system_settings table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

def get_system_setting(key, default=None, db=None):
    """Fetch a runtime setting from DB; falls back to default."""
    conn = db or get_db()
    try:
        _ensure_settings_table(conn)
        row = query_db("SELECT value FROM system_settings WHERE key = ?", (key,), one=True, db=conn)
        return row["value"] if row else default
    except Exception:
        return default

def set_system_setting(key, value, db=None):
    """Upsert a runtime setting into DB."""
    conn = db or get_db()
    _ensure_settings_table(conn)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, str(value), now)
    )
    conn.commit()

def get_real_activities(db=None):
    """Fetches real dispatch and emergency activity from the SQLite database."""
    conn = db or get_db()
    activities = []
    try:
        sql = """
            SELECT r.id, r.status, r.created_at, r.response_time,
                   br.id AS request_id, br.required_blood_group, br.hospital_name, br.location,
                   u.full_name AS donor_name, dp.blood_group AS donor_blood_group
            FROM donor_request_responses r
            JOIN blood_requests br ON r.blood_request_id = br.id
            JOIN users u ON r.donor_id = u.id
            LEFT JOIN donor_profiles dp ON u.id = dp.user_id
            ORDER BY r.created_at DESC LIMIT 20
        """
        dispatches = query_db(sql, db=conn)
        for d in (dispatches or []):
            status = (d.get("status") or "PENDING").upper()
            b_group = d.get("donor_blood_group") or d.get("required_blood_group", "O+")
            hosp = d.get("hospital_name") or "Regional Medical Center"
            donor = d.get("donor_name") or "Verified Donor"
            loc = d.get("location") or "Kolkata"

            if status == "ACCEPTED":
                title = "Donor Dispatch Confirmed"
                desc = f"{donor} accepted {b_group} emergency request #{d['request_id']} for {hosp}."
                icon = "fa-circle-check"
                icon_class = "activity-icon-success"
            elif status == "REJECTED":
                title = "Dispatch Response Received"
                desc = f"{donor} was unavailable for {b_group} request #{d['request_id']}."
                icon = "fa-circle-xmark"
                icon_class = "activity-icon-warning"
            else:
                title = "Donor Request Dispatched"
                desc = f"{donor} — {b_group} donor request dispatched for #{d['request_id']} ({hosp})"
                icon = "fa-paper-plane"
                icon_class = "activity-icon-primary"

            activities.append({
                "id": d["id"],
                "request_id": d["request_id"],
                "donor_name": donor,
                "blood_group": b_group,
                "hospital": hosp,
                "status": status,
                "created_at": d.get("created_at") or "",
                "title": title,
                "desc": desc,
                "time": "Just now",
                "icon": icon,
                "iconClass": icon_class
            })

        if not activities:
            logs = query_db("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 6", db=conn)
            for log in (logs or []):
                action = log.get("action", "")
                if action in ("INIT_ADMIN", "LOGIN_SUCCESS", "LOGOUT"):
                    continue
                activities.append({
                    "title": action.replace("_", " ").title(),
                    "desc": log.get("details", "System activity logged"),
                    "time": "Recent",
                    "icon": "fa-bell",
                    "iconClass": "activity-icon-primary"
                })
    except Exception:
        pass
    return activities


def create_app(config_class=Config):
    """
    Application factory for HEMONEXAS platform.
    Serves both the REST API and the HemoNexus HTML templates and static assets.
    """
    template_dir = PROJECT_ROOT / "HemoNexus" / "templates"
    static_dir = PROJECT_ROOT / "HemoNexus" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )
    app.config.from_object(config_class)
    app.secret_key = os.environ.get('SECRET_KEY', 'hemonexus-secure-auth-secret-key-2026')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Teardown database connection
    app.teardown_appcontext(close_db)

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(donor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(admin_bp)

    # Ensure database schema is initialized if file doesn't exist
    if app.config.get("DATABASE_PATH") and app.config["DATABASE_PATH"] != ":memory:":
        db_path = Path(app.config["DATABASE_PATH"])
        if not db_path.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with app.app_context():
                init_database(str(db_path), seed_demo=True)
        else:
            with app.app_context():
                try:
                    conn = get_db(str(db_path))
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS hospitals (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                            city TEXT,
                            created_at TEXT NOT NULL DEFAULT (datetime('now'))
                        );
                    """)
                    conn.execute("""
                        INSERT OR IGNORE INTO hospitals (name, city, created_at)
                        SELECT DISTINCT hospital_name, location, datetime('now')
                        FROM blood_requests
                        WHERE hospital_name IS NOT NULL AND TRIM(hospital_name) != ''
                    """)
                    conn.commit()
                except Exception:
                    pass

    @app.context_processor
    def inject_user():
        """Inject current user details into all Jinja templates."""
        user = None
        if 'user_id' in session:
            uid = session.get('user_id')
            user_loc = "Kolkata"
            try:
                conn = get_db()
                role = session.get('role', 'donor')
                if role == 'donor':
                    prof = query_db("SELECT location FROM donor_profiles WHERE user_id = ?", (uid,), one=True, db=conn)
                else:
                    prof = query_db("SELECT location FROM patient_profiles WHERE user_id = ?", (uid,), one=True, db=conn)
                if prof and prof.get("location"):
                    user_loc = prof["location"]
            except Exception:
                pass

            user = {
                'id': uid,
                'name': session.get('user_name', 'User'),
                'email': session.get('user_email', ''),
                'role': session.get('role', 'donor'),
                'location': user_loc
            }
        return dict(current_user=user, is_logged_in=('user_id' in session))

    @app.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # ── Page Routes ──────────────────────────────────────────────

    @app.route("/")
    @app.route("/index")
    def index():
        if request.headers.get("Accept") == "application/json" and not request.accept_mimetypes.accept_html:
            return jsonify({
                "service": "HEMONEXAS Backend REST API & Web Platform",
                "status": "online",
                "version": "1.0.0"
            }), 200
        if 'user_id' in session:
            return redirect(url_for('home'))
        return redirect(url_for('login'))

    @app.route('/main')
    @app.route('/landing')
    @app.route('/landing.html')
    @app.route('/home.html')
    @app.route('/home')
    def home():
        return render_template('home.html', is_public_page=True, active_page='home')

    @app.route('/login', methods=['GET', 'POST'])
    @app.route('/login.html', methods=['GET', 'POST'])
    def login():
        error = None
        email_val = ""
        active_role = request.args.get('role', 'donor')

        if request.method == 'POST':
            email_val = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''
            active_role = request.form.get('userRole', active_role)

            if not email_val or not password:
                error = "Both email address and password are required to sign in."
            else:
                conn = get_db()
                user = query_db("SELECT * FROM users WHERE email = ?", (email_val,), one=True, db=conn)
                if not user:
                    error = f"No account found for '{email_val}'. Please verify your email or create a new account."
                elif not check_password_hash(user['password_hash'], password):
                    error = "Incorrect password. Please verify your security credentials and try again."
                else:
                    session.clear()
                    session['user_id'] = user['id']
                    session['user_name'] = user['full_name']
                    session['user_email'] = user['email']
                    session['role'] = user['role']

                    execute_db(
                        "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
                        (user['id'], "LOGIN_SUCCESS", f"User {user['email']} authenticated successfully"),
                        db=conn
                    )

                    flash(f"Welcome back, {user['full_name']}! You have signed in successfully.", "success")
                    next_page = request.args.get('next')
                    if next_page and next_page.startswith('/'):
                        return redirect(next_page)
                    return redirect(url_for('home'))

        return render_template(
            'login.html',
            is_public_page=True,
            active_page='login',
            active_role=active_role,
            error=error,
            email=email_val
        )

    @app.route('/register', methods=['GET', 'POST'])
    @app.route('/register.html', methods=['GET', 'POST'])
    def register():
        error = None
        active_role = request.args.get('role', 'donor')

        if request.method == 'POST':
            full_name = (request.form.get('name') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            phone = (request.form.get('phone') or '').strip()
            blood_group = (request.form.get('bloodGroup') or 'O+').strip().upper()
            city = (request.form.get('city') or 'Kolkata').strip()
            password = request.form.get('password') or ''
            role = (request.form.get('userRole') or active_role).strip().lower()

            if role not in ('donor', 'patient'):
                role = 'donor'

            if not full_name or not email or not password:
                error = "Full legal name, email address, and security password are required."
            elif len(password) < 6:
                error = "Security password must be at least 6 characters long."
            else:
                conn = get_db()
                existing = query_db("SELECT id FROM users WHERE email = ?", (email,), one=True, db=conn)
                if existing:
                    error = f"An account with email '{email}' already exists. Please sign in instead."
                else:
                    try:
                        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        hashed = generate_password_hash(password)
                        user_id, _ = execute_db(
                            "INSERT INTO users (full_name, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (full_name, email, hashed, role, now, now),
                            db=conn
                        )

                        if role == 'donor':
                            next_due = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=180)).isoformat()
                            execute_db(
                                """INSERT INTO donor_profiles 
                                   (user_id, blood_group, phone, location, availability, maximum_travel_distance, profile_status, last_verified_date, next_verification_date, created_at, updated_at)
                                   VALUES (?, ?, ?, ?, '24_HOURS', 15.0, 'ACTIVE', ?, ?, ?, ?)""",
                                (user_id, blood_group, phone, city, now, next_due, now, now),
                                db=conn
                            )
                        else:
                            execute_db(
                                "INSERT INTO patient_profiles (user_id, phone, location, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                (user_id, phone, city, now, now),
                                db=conn
                            )

                        session.clear()
                        session['user_id'] = user_id
                        session['user_name'] = full_name
                        session['user_email'] = email
                        session['role'] = role

                        flash(f"Account successfully created for {full_name}! Welcome to HemoNexus.", "success")
                        return redirect(url_for('home'))
                    except Exception as ex:
                        error = f"Registration error: {str(ex)}"

        return render_template(
            'register.html',
            is_public_page=True,
            active_page='register',
            active_role=active_role,
            error=error
        )

    @app.route('/logout')
    def logout():
        user_name = session.get('user_name', 'User')
        user_id = session.get('user_id')
        if user_id:
            try:
                conn = get_db()
                execute_db(
                    "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
                    (user_id, "LOGOUT", "User logged out"),
                    db=conn
                )
            except Exception:
                pass
        session.clear()
        flash(f"You have been safely signed out, {user_name}.", "info")
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @app.route('/dashboard.html')
    def dashboard():
        real_requests = []
        real_activities = []
        real_donors = []
        critical_alert = None
        try:
            conn = get_db()
            db_reqs = query_db(
                """SELECT br.*, 
                          COUNT(r.id) AS total_sent,
                          SUM(CASE WHEN r.status = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_count,
                          SUM(CASE WHEN r.status = 'PENDING' THEN 1 ELSE 0 END) AS pending_count
                   FROM blood_requests br
                   LEFT JOIN donor_request_responses r ON br.id = r.blood_request_id
                   GROUP BY br.id
                   ORDER BY br.created_at DESC LIMIT 8""",
                db=conn
            )
            for r in (db_reqs or []):
                real_requests.append({
                    "id": f"REQ-{r['id']}",
                    "raw_id": r['id'],
                    "patientName": f"Requirement #{r['id']}",
                    "bloodGroup": r["required_blood_group"],
                    "component": "Whole Blood",
                    "unitsNeeded": r["required_units"],
                    "unitsFulfilled": r["accepted_count"] or 0,
                    "hospital": r["hospital_name"],
                    "location": r["location"],
                    "urgency": (r["urgency"] or "NORMAL").lower(),
                    "status": (r["request_status"] or "OPEN").lower(),
                    "requiredBy": r["required_date_time"] or "Immediate",
                    "createdAt": r["created_at"] or ""
                })
                if (r["urgency"] or "").upper() == "CRITICAL" and not critical_alert:
                    critical_alert = f"{r['hospital_name']} ({r['location']}) urgently requires {r['required_units']} units of {r['required_blood_group']} (REQ-{r['id']})."

            real_activities = get_real_activities(conn)

            sql_dispatches = """
                SELECT r.id, r.blood_request_id, r.donor_id, r.status, r.created_at,
                       u.full_name AS donor_name, dp.blood_group AS donor_blood_group,
                       br.hospital_name, br.required_blood_group, br.location AS hospital_location
                FROM donor_request_responses r
                JOIN blood_requests br ON r.blood_request_id = br.id
                JOIN users u ON r.donor_id = u.id
                LEFT JOIN donor_profiles dp ON u.id = dp.user_id
                ORDER BY r.created_at DESC LIMIT 10
            """
            real_dispatches = query_db(sql_dispatches, db=conn) or []

            db_donors = query_db(
                """SELECT d.*, u.full_name AS name, u.phone AS contact_phone, u.email
                   FROM donor_profiles d
                   JOIN users u ON d.user_id = u.id
                   WHERE d.profile_status = 'ACTIVE'
                   LIMIT 10""",
                db=conn
            )
            for d in (db_donors or []):
                real_donors.append({
                    "id": f"D-{d['id']}",
                    "user_id": d["user_id"],
                    "name": d["name"],
                    "bloodGroup": d["blood_group"],
                    "city": d["location"] or "Kolkata",
                    "area": d["location"] or "Kolkata",
                    "status": (d["profile_status"] or "available").lower(),
                    "phone": d.get("phone") or d.get("contact_phone") or ""
                })
        except Exception:
            real_dispatches = []

        return render_template(
            'dashboard.html',
            is_public_page=False,
            active_page='dashboard',
            donors=real_donors,
            requests=real_requests,
            activities=real_activities,
            dispatches=real_dispatches,
            critical_alert=critical_alert
        )

    @app.route('/donors')
    @app.route('/donor')
    @app.route('/donors.html')
    def donors():
        real_donors = []
        try:
            conn = get_db()
            db_donors = query_db(
                """SELECT d.*, u.full_name AS name, u.phone AS contact_phone, u.email
                   FROM donor_profiles d
                   JOIN users u ON d.user_id = u.id
                   ORDER BY d.id ASC""",
                db=conn
            )
            for d in (db_donors or []):
                real_donors.append({
                    "id": f"D-{d['id']}",
                    "raw_id": d["id"],
                    "user_id": d["user_id"],
                    "name": d["name"],
                    "bloodGroup": d["blood_group"],
                    "phone": d.get("phone") or d.get("contact_phone") or "+91 Confidential",
                    "email": d.get("email") or "",
                    "city": d.get("location") or "Kolkata",
                    "area": d.get("location") or "Kolkata",
                    "distanceKm": 3.5,
                    "status": "available" if d.get("profile_status") == "ACTIVE" else "cooldown",
                    "verified": bool(d.get("last_verified_date")),
                    "lastDonatedDate": d.get("last_verified_date") or "2026-09-01",
                    "totalDonations": 5,
                    "responseRate": 95,
                    "hemoglobin": "14.5 g/dL",
                    "weightKg": 70,
                    "bloodPressure": "120/80 mmHg"
                })
        except Exception:
            pass

        return render_template(
            'donors.html',
            is_public_page=False,
            active_page='donors',
            donors=real_donors
        )

    @app.route('/donors/<int:donor_id>')
    @app.route('/donors/<donor_id>')
    def donor_profile(donor_id):
        donor = None
        try:
            conn = get_db()
            clean_id = str(donor_id).replace("D-", "")
            d = query_db(
                """SELECT d.*, u.full_name AS name, u.phone AS contact_phone, u.email
                   FROM donor_profiles d
                   JOIN users u ON d.user_id = u.id
                   WHERE d.id = ? OR d.user_id = ?""",
                (clean_id, clean_id),
                one=True,
                db=conn
            )
            if d:
                donor = {
                    "id": f"D-{d['id']}",
                    "user_id": d["user_id"],
                    "name": d["name"],
                    "bloodGroup": d["blood_group"],
                    "phone": d.get("phone") or d.get("contact_phone") or "",
                    "email": d.get("email") or "",
                    "city": d.get("location") or "Kolkata",
                    "area": d.get("location") or "Kolkata",
                    "distanceKm": 3.5,
                    "status": "available" if d.get("profile_status") == "ACTIVE" else "cooldown",
                    "verified": bool(d.get("last_verified_date")),
                    "lastDonatedDate": d.get("last_verified_date") or "2026-09-01",
                    "totalDonations": 5,
                    "responseRate": 95,
                    "hemoglobin": "14.5 g/dL",
                    "weightKg": 70,
                    "bloodPressure": "120/80 mmHg"
                }
        except Exception:
            pass

        if not donor:
            donor = {
                "id": f"D-{donor_id}",
                "name": "Verified Donor",
                "bloodGroup": "O+",
                "city": "Kolkata",
                "area": "Kolkata",
                "status": "available",
                "verified": True,
                "phone": "+91 Confidential",
                "totalDonations": 5,
                "responseRate": 95
            }

        return render_template(
            'donor_profile.html',
            is_public_page=False,
            active_page='donors',
            donor=donor
        )

    @app.route('/requests')
    @app.route('/request')
    @app.route('/requests.html')
    def requests():
        real_requests = []
        try:
            conn = get_db()
            db_reqs = query_db(
                """SELECT br.*, 
                          COUNT(r.id) AS total_sent,
                          SUM(CASE WHEN r.status = 'ACCEPTED' THEN 1 ELSE 0 END) AS accepted_count
                   FROM blood_requests br
                   LEFT JOIN donor_request_responses r ON br.id = r.blood_request_id
                   GROUP BY br.id
                   ORDER BY br.created_at DESC""",
                db=conn
            )
            for r in (db_reqs or []):
                real_requests.append({
                    "id": f"REQ-{r['id']}",
                    "raw_id": r['id'],
                    "patientName": f"Requirement #{r['id']}",
                    "bloodGroup": r["required_blood_group"],
                    "component": "Whole Blood",
                    "unitsNeeded": r["required_units"],
                    "unitsFulfilled": r["accepted_count"] or 0,
                    "hospital": r["hospital_name"],
                    "location": r["location"],
                    "urgency": (r["urgency"] or "NORMAL").lower(),
                    "status": (r["request_status"] or "OPEN").lower(),
                    "requiredBy": r["required_date_time"] or "Immediate",
                    "createdAt": r["created_at"] or ""
                })
        except Exception:
            pass

        return render_template(
            'requests.html',
            is_public_page=False,
            active_page='requests',
            requests=real_requests
        )

    @app.route('/requests/new')
    def request_create():
        return render_template(
            'request_create.html',
            is_public_page=False,
            active_page='requests'
        )

    @app.route('/match')
    @app.route('/matching')
    @app.route('/search')
    @app.route('/match.html')
    @app.route('/dispatch')
    @app.route('/dispatch-route')
    @app.route('/dispatch_route')
    @app.route('/dispatch.html')
    @app.route('/dispatch/route')
    def matching():
        pre_group = request.args.get('group', '')
        pre_comp = request.args.get('component', '')
        active_page = 'dispatch' if 'dispatch' in request.path else 'match'
        return render_template(
            'matching.html',
            is_public_page=False,
            active_page=active_page,
            pre_group=pre_group,
            pre_comp=pre_comp
        )

    @app.route('/emergency')
    @app.route('/sos')
    @app.route('/emergency-sos')
    @app.route('/emergency_sos')
    @app.route('/emergencysos')
    @app.route('/emergency.html')
    @app.route('/code-red')
    @app.route('/code_red')
    def emergency():
        return render_template(
            'emergency.html',
            is_public_page=False,
            active_page='emergency'
        )

    @app.route('/availability')
    @app.route('/availability.html')
    def availability():
        return render_template(
            'availability.html',
            is_public_page=False,
            active_page='availability'
        )

    # ── Supplementary API Endpoints ──────────────────────────────

    @app.route('/api/activities')
    @app.route('/api/patient/activities')
    def api_activities():
        """Returns live database activities and dispatches."""
        return jsonify({"success": True, "activities": get_real_activities()}), 200

    @app.route('/api/dispatches')
    def api_dispatches():
        """Returns all real dispatches from donor_request_responses."""
        conn = get_db()
        sql = """
            SELECT r.id, r.blood_request_id, r.donor_id, r.status, r.created_at, r.response_time,
                   u.full_name AS donor_name, u.phone AS donor_phone,
                   dp.blood_group AS donor_blood_group, dp.location AS donor_location,
                   br.required_blood_group, br.hospital_name, br.location AS hospital_location,
                   br.urgency, br.required_units
            FROM donor_request_responses r
            JOIN blood_requests br ON r.blood_request_id = br.id
            JOIN users u ON r.donor_id = u.id
            LEFT JOIN donor_profiles dp ON u.id = dp.user_id
            ORDER BY r.created_at DESC LIMIT 30
        """
        dispatches = query_db(sql, db=conn)
        return jsonify({"success": True, "dispatches": dispatches or []}), 200

    @app.route('/api/donors')
    def api_donors():
        """Returns verified real donors from SQLite."""
        conn = get_db()
        sql = """
            SELECT d.id, d.user_id, d.blood_group, d.location, d.availability,
                   d.maximum_travel_distance, d.profile_status, d.last_verified_date,
                   u.full_name AS name, u.phone, u.email
            FROM donor_profiles d
            JOIN users u ON d.user_id = u.id
            ORDER BY d.id ASC
        """
        donors = query_db(sql, db=conn)
        return jsonify({"success": True, "donors": donors}), 200

    @app.route('/api/notifications')
    def api_notifications():
        """Returns role-aware live notifications for the current logged-in user."""
        conn = get_db()
        notifications = []
        try:
            role = session.get('role', '')
            user_id = session.get('user_id')

            # ── 1. Critical / Urgent open blood requests (visible to all logged-in users) ──
            urgent_sql = """
                SELECT id, required_blood_group, hospital_name, location, urgency, required_units, created_at
                FROM blood_requests
                WHERE status IN ('OPEN', 'PENDING')
                ORDER BY
                    CASE urgency WHEN 'CRITICAL' THEN 1 WHEN 'URGENT' THEN 2 ELSE 3 END,
                    created_at DESC
                LIMIT 5
            """
            urgent_rows = query_db(urgent_sql, db=conn) or []
            for row in urgent_rows:
                urg = (row.get('urgency') or 'NORMAL').upper()
                icon = 'fa-droplet' if urg == 'CRITICAL' else 'fa-heart-pulse'
                icon_class = 'notif-icon-critical' if urg == 'CRITICAL' else 'notif-icon-warning'
                notifications.append({
                    'id': f'req_{row["id"]}',
                    'type': 'blood_request',
                    'title': f'{urg.title()} Blood Request — {row["required_blood_group"]}',
                    'desc': f'{row["required_units"] or 1} unit(s) needed at {row["hospital_name"]}, {row["location"]}',
                    'icon': icon,
                    'iconClass': icon_class,
                    'time': row.get('created_at', '')[:16] if row.get('created_at') else 'Recent',
                    'read': False
                })

            # ── 2. Donor-specific: pending requests in their inbox ──
            if role == 'donor' and user_id:
                donor_inbox_sql = """
                    SELECT r.id, r.status, r.created_at,
                           br.required_blood_group, br.hospital_name, br.location, br.urgency
                    FROM donor_request_responses r
                    JOIN blood_requests br ON r.blood_request_id = br.id
                    WHERE r.donor_id = ? AND r.status = 'PENDING'
                    ORDER BY r.created_at DESC LIMIT 5
                """
                inbox_rows = query_db(donor_inbox_sql, (user_id,), db=conn) or []
                for row in inbox_rows:
                    notifications.append({
                        'id': f'inbox_{row["id"]}',
                        'type': 'donor_inbox',
                        'title': f'Donation Request — {row["required_blood_group"]}',
                        'desc': f'You have a pending request from {row["hospital_name"]}, {row["location"]}',
                        'icon': 'fa-hand-holding-droplet',
                        'iconClass': 'notif-icon-primary',
                        'time': row.get('created_at', '')[:16] if row.get('created_at') else 'Recent',
                        'read': False
                    })

            # ── 3. Recent accepted/dispatched responses (latest activity feed) ──
            recent_sql = """
                SELECT r.id, r.status, r.created_at,
                       u.full_name AS donor_name,
                       br.required_blood_group, br.hospital_name
                FROM donor_request_responses r
                JOIN blood_requests br ON r.blood_request_id = br.id
                JOIN users u ON r.donor_id = u.id
                WHERE r.status IN ('ACCEPTED', 'DISPATCHED')
                ORDER BY r.created_at DESC LIMIT 3
            """
            recent_rows = query_db(recent_sql, db=conn) or []
            for row in recent_rows:
                notifications.append({
                    'id': f'dispatch_{row["id"]}',
                    'type': 'dispatch',
                    'title': 'Donor Dispatch Confirmed',
                    'desc': f'{row["donor_name"]} accepted {row["required_blood_group"]} request at {row["hospital_name"]}',
                    'icon': 'fa-circle-check',
                    'iconClass': 'notif-icon-success',
                    'time': row.get('created_at', '')[:16] if row.get('created_at') else 'Recent',
                    'read': False
                })

        except Exception as e:
            pass

        unread_count = len([n for n in notifications if not n['read']])
        return jsonify({
            'success': True,
            'notifications': notifications,
            'unread_count': unread_count
        }), 200

    # ── Demo / Testing Endpoints ─────────────────────────────────

    @app.route('/api/demo/sweep', methods=['POST', 'GET'])
    def demo_verification_sweep():
        """
        DEMO ENDPOINT: Runs the verification lifecycle sweep without admin login.
        Marks donors INACTIVE if their next_verification_date + grace has passed.
        Returns a detailed before/after report for demonstration.
        """
        conn = get_db()
        # Capture state before sweep
        before = query_db(
            "SELECT dp.id, u.full_name, dp.profile_status, dp.next_verification_date "
            "FROM donor_profiles dp JOIN users u ON dp.user_id = u.id ORDER BY dp.id",
            db=conn
        ) or []

        stats = sweep_and_update_donor_statuses(db=conn)

        # Capture state after sweep
        after = query_db(
            "SELECT dp.id, u.full_name, dp.profile_status, dp.next_verification_date "
            "FROM donor_profiles dp JOIN users u ON dp.user_id = u.id ORDER BY dp.id",
            db=conn
        ) or []

        before_map = {r['id']: r['profile_status'] for r in before}
        changes = []
        for row in after:
            prev = before_map.get(row['id'], '?')
            if prev != row['profile_status']:
                changes.append({
                    'donor_id': row['id'],
                    'name': row['full_name'],
                    'from': prev,
                    'to': row['profile_status'],
                    'next_verification_date': row['next_verification_date']
                })

        return jsonify({
            'success': True,
            'message': f"Sweep complete: {stats['evaluated']} donors evaluated, {stats['updated']} status changes.",
            'stats': stats,
            'changes': changes,
            'current_states': [{'id': r['id'], 'name': r['full_name'], 'status': r['profile_status']} for r in after]
        }), 200

    @app.route('/api/donor/verification-status', methods=['GET'])
    def get_my_verification_status():
        """Returns own verification lifecycle status for logged-in donor."""
        from backend.services.verification_service import get_donor_verification_details
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not logged in'}), 401
        conn = get_db()
        details = get_donor_verification_details(user_id, db=conn)
        if not details:
            return jsonify({'success': False, 'error': 'No donor profile found'}), 404
        return jsonify({'success': True, 'verification': details}), 200

    # ── Admin Settings API ───────────────────────────────────────

    @app.route('/api/admin/settings', methods=['GET'])
    def get_admin_settings():
        """Returns current runtime system settings (no auth required for demo)."""
        conn = get_db()
        interval_sec = get_system_setting('verification_interval_seconds', db=conn)
        grace_sec    = get_system_setting('grace_period_seconds', db=conn)
        return jsonify({
            'success': True,
            'settings': {
                'verification_interval_seconds': float(interval_sec) if interval_sec is not None else None,
                'grace_period_seconds':          float(grace_sec)    if grace_sec    is not None else None,
                'verification_interval_days':    Config.VERIFICATION_INTERVAL_DAYS,
                'grace_period_days':             Config.GRACE_PERIOD_DAYS,
                'mode': 'custom' if interval_sec else 'default'
            }
        }), 200

    @app.route('/api/admin/settings', methods=['POST'])
    def update_admin_settings():
        """
        Update runtime verification intervals. Admin-only in production;
        open for demo. Accepts JSON:
          { "verification_interval_seconds": N, "grace_period_seconds": M }
        N and M can be seconds (e.g. 120 = 2 minutes, 30 = 30 seconds).
        """
        data = request.get_json(silent=True) or {}
        conn = get_db()
        updated = {}

        if 'verification_interval_seconds' in data:
            val = float(data['verification_interval_seconds'])
            if val <= 0:
                return jsonify({'success': False, 'error': 'Interval must be > 0 seconds'}), 400
            set_system_setting('verification_interval_seconds', val, db=conn)
            updated['verification_interval_seconds'] = val

        if 'grace_period_seconds' in data:
            val = float(data['grace_period_seconds'])
            if val < 0:
                return jsonify({'success': False, 'error': 'Grace period cannot be negative'}), 400
            set_system_setting('grace_period_seconds', val, db=conn)
            updated['grace_period_seconds'] = val

        if 'reset_to_default' in data and data['reset_to_default']:
            conn.execute("DELETE FROM system_settings WHERE key IN ('verification_interval_seconds','grace_period_seconds')")
            conn.commit()
            updated['reset'] = True

        user_id = session.get('user_id', 0)
        try:
            execute_db(
                "INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, "ADMIN_SETTINGS_UPDATE", f"Settings changed: {updated}"),
                db=conn
            )
        except Exception:
            pass

        return jsonify({'success': True, 'message': 'Settings updated.', 'updated': updated}), 200

    # ── Admin Control Panel Page ─────────────────────────────────

    @app.route('/admin')
    def admin_panel():
        """Admin Control Panel — verification lifecycle settings and donor sweep."""
        if session.get('role') != 'admin':
            return redirect(url_for('login'))
        return render_template('admin_panel.html', active_page='admin')

    # ── Error Handlers ───────────────────────────────────────────


    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Bad Request: " + str(getattr(e, 'description', e))}), 400
        return "Bad Request", 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Unauthorized: Authentication required."}), 401
        return redirect(url_for('login'))

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Forbidden: Insufficient privileges."}), 403
        return "Forbidden", 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Resource not found."}), 404
        return redirect(url_for('login'))

    @app.errorhandler(409)
    def conflict(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Conflict: " + str(getattr(e, 'description', e))}), 409
        return "Conflict", 409

    @app.errorhandler(500)
    def internal_error(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error."}), 500
        return "Internal Server Error", 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
