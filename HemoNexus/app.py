"""
HemoNexus - Smart Blood Donor Management & Requirement-Based Matching System
Flask Application Entry Point with SQLite Authentication & Session Security
"""

import os
import sys
import datetime
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import Config
from backend.database import get_db, close_db, query_db, execute_db
from backend.init_db import init_database
from backend.database_service import (
    authenticate_user,
    get_user_by_email,
    get_user_by_id,
    create_user,
    create_donor,
    validate_email
)
from backend.routes.auth import auth_bp
from backend.routes.donor import donor_bp
from backend.routes.patient import patient_bp
from backend.routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.environ.get('SECRET_KEY', 'hemonexus-secure-auth-secret-key-2026')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Register database teardown
app.teardown_appcontext(close_db)

# Register REST API Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(donor_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(admin_bp)

# Ensure database exists and is initialized
with app.app_context():
    db_file = Path(Config.DATABASE_PATH)
    if not db_file.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)
        init_database(str(db_file), seed_demo=True)


def login_required_web(f):
    """Decorator to require login for sensitive web pages."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this portal section.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_user():
    """Inject current user details into all Jinja templates with profile location."""
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
            if prof and prof["location"]:
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


# Sample Mock Data Context
DONORS = [
    {
        "id": "D-101",
        "name": "Aarav Sharma",
        "bloodGroup": "O-",
        "gender": "Male",
        "age": 29,
        "phone": "+91 98765 43210",
        "email": "aarav.sharma@example.com",
        "city": "Kolkata",
        "area": "Park Street",
        "distanceKm": 2.4,
        "status": "available",
        "verified": True,
        "lastDonatedDate": "2026-04-10",
        "totalDonations": 12,
        "responseRate": 98,
        "hemoglobin": "15.2 g/dL",
        "weightKg": 74,
        "bloodPressure": "120/80 mmHg"
    },
    {
        "id": "D-102",
        "name": "Pooja Nair",
        "bloodGroup": "A+",
        "gender": "Female",
        "age": 26,
        "phone": "+91 98123 45678",
        "email": "pooja.nair@example.com",
        "city": "Kolkata",
        "area": "Salt Lake Sector V",
        "distanceKm": 4.1,
        "status": "available",
        "verified": True,
        "lastDonatedDate": "2026-03-15",
        "totalDonations": 8,
        "responseRate": 95,
        "hemoglobin": "13.8 g/dL",
        "weightKg": 62,
        "bloodPressure": "118/76 mmHg"
    },
    {
        "id": "D-103",
        "name": "Rohan Deshmukh",
        "bloodGroup": "B+",
        "gender": "Male",
        "age": 34,
        "phone": "+91 97654 32109",
        "email": "rohan.d@example.com",
        "city": "Kolkata",
        "area": "Bhowanipore",
        "distanceKm": 7.8,
        "status": "cooldown",
        "verified": True,
        "lastDonatedDate": "2026-07-28",
        "totalDonations": 15,
        "responseRate": 92,
        "hemoglobin": "14.6 g/dL",
        "weightKg": 80,
        "bloodPressure": "122/82 mmHg"
    },
    {
        "id": "D-104",
        "name": "Ananya Sengupta",
        "bloodGroup": "AB+",
        "gender": "Female",
        "age": 24,
        "phone": "+91 98450 11223",
        "email": "ananya.s@example.com",
        "city": "Kolkata",
        "area": "New Town",
        "distanceKm": 3.5,
        "status": "available",
        "verified": True,
        "lastDonatedDate": "2026-02-18",
        "totalDonations": 6,
        "responseRate": 100,
        "hemoglobin": "13.4 g/dL",
        "weightKg": 58,
        "bloodPressure": "116/74 mmHg"
    },
    {
        "id": "D-105",
        "name": "Vikram Mehta",
        "bloodGroup": "O+",
        "gender": "Male",
        "age": 38,
        "phone": "+91 98200 99887",
        "email": "vikram.m@example.com",
        "city": "Mumbai",
        "area": "Andheri West",
        "distanceKm": 1.8,
        "status": "available",
        "verified": True,
        "lastDonatedDate": "2026-05-02",
        "totalDonations": 21,
        "responseRate": 99,
        "hemoglobin": "15.8 g/dL",
        "weightKg": 84,
        "bloodPressure": "124/80 mmHg"
    },
    {
        "id": "D-106",
        "name": "Kavita Patel",
        "bloodGroup": "AB-",
        "gender": "Female",
        "age": 31,
        "phone": "+91 98980 44556",
        "email": "kavita.p@example.com",
        "city": "Delhi",
        "area": "Connaught Place",
        "distanceKm": 6.2,
        "status": "available",
        "verified": True,
        "lastDonatedDate": "2026-01-20",
        "totalDonations": 9,
        "responseRate": 90,
        "hemoglobin": "13.1 g/dL",
        "weightKg": 65,
        "bloodPressure": "120/78 mmHg"
    }
]

REQUESTS = [
    {
        "id": "REQ-4091",
        "patientName": "Kunal Singhania",
        "bloodGroup": "O-",
        "component": "Whole Blood",
        "unitsNeeded": 3,
        "unitsFulfilled": 2,
        "hospital": "AMRI Hospital, Dhakuria",
        "location": "Park Street, Kolkata",
        "urgency": "critical",
        "status": "in-progress",
        "requiredBy": "2026-08-27 04:00 AM",
        "createdAt": "23:15 PM",
        "contactPhone": "+91 98222 00112"
    },
    {
        "id": "REQ-4092",
        "patientName": "Sneha Verma",
        "bloodGroup": "A+",
        "component": "Platelets",
        "unitsNeeded": 2,
        "unitsFulfilled": 1,
        "hospital": "Tata Medical Center",
        "location": "New Town, Kolkata",
        "urgency": "urgent",
        "status": "matched",
        "requiredBy": "2026-08-27 10:00 AM",
        "createdAt": "21:30 PM",
        "contactPhone": "+91 98111 22334"
    },
    {
        "id": "REQ-4093",
        "patientName": "Devendra Joshi",
        "bloodGroup": "B+",
        "component": "RBC",
        "unitsNeeded": 2,
        "unitsFulfilled": 2,
        "hospital": "SSKM Hospital",
        "location": "Bhowanipore, Kolkata",
        "urgency": "routine",
        "status": "fulfilled",
        "requiredBy": "2026-08-27 02:00 PM",
        "createdAt": "14:00 PM",
        "contactPhone": "+91 98333 44556"
    }
]

ACTIVITIES = []

def get_real_activities(db=None):
    """Fetches real dispatch and emergency activity from the SQLite database."""
    conn = db or get_db()
    activities = []
    try:
        # Real donor dispatch responses from database
        sql = """
            SELECT r.id, r.status, r.created_at, r.response_time,
                   br.id AS request_id, br.required_blood_group, br.hospital_name, br.location,
                   u.full_name AS donor_name
            FROM donor_request_responses r
            JOIN blood_requests br ON r.blood_request_id = br.id
            JOIN users u ON r.donor_id = u.id
            ORDER BY r.created_at DESC LIMIT 8
        """
        dispatches = query_db(sql, db=conn)
        for d in (dispatches or []):
            status = d.get("status", "PENDING")
            b_group = d.get("required_blood_group", "O+")
            hosp = d.get("hospital_name") or "Regional Medical Center"
            donor = d.get("donor_name") or "Verified Donor"
            loc = d.get("location") or "Kolkata"

            if status == "ACCEPTED":
                title = "Donor Dispatch Confirmed"
                desc = f"{donor} accepted {b_group} emergency request #{d['request_id']} for {hosp}."
                icon = "fa-truck-medical"
                icon_class = "stat-icon-success"
            elif status == "REJECTED":
                title = "Dispatch Response Received"
                desc = f"{donor} was unavailable for {b_group} request #{d['request_id']}."
                icon = "fa-circle-xmark"
                icon_class = "stat-icon-warning"
            else:
                title = "Donor Request Dispatched"
                desc = f"{b_group} requirement invitation sent to {donor} for {hosp} ({loc})."
                icon = "fa-paper-plane"
                icon_class = "stat-icon-primary"

            activities.append({
                "title": title,
                "desc": desc,
                "time": "Just now",
                "icon": icon,
                "iconClass": icon_class
            })

        # If no dispatches yet, check audit_logs
        if not activities:
            logs = query_db("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 5", db=conn)
            for log in (logs or []):
                action = log.get("action", "")
                if action in ("INIT_ADMIN", "LOGIN_SUCCESS", "LOGOUT"):
                    continue
                activities.append({
                    "title": action.replace("_", " ").title(),
                    "desc": log.get("details", "System activity logged"),
                    "time": "Recent",
                    "icon": "fa-bell",
                    "iconClass": "stat-icon-primary"
                })
    except Exception:
        pass
    return activities


@app.route('/')
@app.route('/index')
@app.route('/index.html')
def index():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


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
            # 1. Look up user by email in the SQLite database
            user = get_user_by_email(email_val)
            if not user:
                # Security: Unregistered users cannot login
                error = f"No account found for '{email_val}'. Please verify your email or create a new account."
            # 2. Cryptographic password verification (PBKDF2/scrypt)
            elif not check_password_hash(user['password_hash'], password):
                # Security: Registered users with incorrect passwords cannot login
                error = "Incorrect password. Please verify your security credentials and try again."
            else:
                # 3. Successful secure authentication
                session.clear()
                session['user_id'] = user['id']
                session['user_name'] = user['full_name']
                session['user_email'] = user['email']
                session['role'] = user['role']

                # Log audit trail
                conn = get_db()
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
        city = (request.form.get('city') or '').strip()
        password = request.form.get('password') or ''
        role = (request.form.get('userRole') or active_role).strip().lower()

        if role not in ('donor', 'patient'):
            role = 'donor'

        # Validation checks
        if not full_name or not email or not password:
            error = "Full legal name, email address, and security password are required."
        elif len(password) < 6:
            error = "Security password must be at least 6 characters long."
        else:
            is_valid_email, email_or_err = validate_email(email)
            if not is_valid_email:
                error = "Please enter a valid email address format (e.g., name@example.com)."
            else:
                existing = get_user_by_email(email)
                if existing:
                    error = f"An account with email '{email}' already exists. Please sign in instead."
                else:
                    try:
                        conn = get_db()
                        # Insert new user with secure password hash
                        new_user = create_user(
                            full_name=full_name,
                            email=email,
                            password=password,
                            role=role,
                            phone=phone,
                            db=conn
                        )
                        user_id = new_user['id']

                        # Create role-specific profile
                        if role == 'donor':
                            create_donor(
                                user_id=user_id,
                                blood_group=blood_group,
                                location=city or "Kolkata",
                                phone=phone,
                                availability_type="24_HOURS",
                                max_distance_km=15.0,
                                status="ACTIVE",
                                db=conn
                            )
                        elif role == 'patient':
                            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            execute_db(
                                "INSERT INTO patient_profiles (user_id, phone, location, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                                (user_id, phone, city or "Kolkata", now, now),
                                db=conn
                            )

                        flash(f"Account successfully created for {full_name}! Please sign in with your credentials.", "success")
                        return redirect(url_for('login', role=role))
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
@app.route('/logout.html')
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


@app.route('/home')
@app.route('/home.html')
@app.route('/landing')
@app.route('/landing.html')
@app.route('/main')
def home():
    # Main product homepage
    return render_template('home.html', is_public_page=True, active_page='home')


@app.route('/dashboard')
@app.route('/dashboard.html')
def dashboard():
    real_requests = []
    real_activities = []
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
               ORDER BY br.created_at DESC LIMIT 5""",
            db=conn
        )
        if db_reqs:
            for r in db_reqs:
                real_requests.append({
                    "id": f"REQ-{r['id']}",
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
                    "createdAt": r["created_at"] or "",
                    "contactPhone": "+91 98222 00112"
                })
                if (r["urgency"] or "").upper() == "CRITICAL" and not critical_alert:
                    critical_alert = f"{r['hospital_name']} ({r['location']}) urgently requires {r['required_units']} units of {r['required_blood_group']} (REQ-{r['id']})."

        real_activities = get_real_activities(conn)
    except Exception:
        pass

    return render_template(
        'dashboard.html',
        is_public_page=False,
        active_page='dashboard',
        donors=DONORS,
        requests=real_requests,
        activities=real_activities,
        critical_alert=critical_alert
    )


@app.route('/api/activities')
@app.route('/api/patient/activities')
def api_activities():
    """Returns live database activities and dispatches for the dashboard."""
    return jsonify({"success": True, "activities": get_real_activities()}), 200


@app.route('/donors')
@app.route('/donor')
@app.route('/donors.html')
def donors():
    return render_template(
        'donors.html',
        is_public_page=False,
        active_page='donors',
        donors=DONORS
    )


@app.route('/donors/<donor_id>')
def donor_profile(donor_id):
    donor = next((d for d in DONORS if d['id'] == donor_id), DONORS[0])
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
    return render_template(
        'requests.html',
        is_public_page=False,
        active_page='requests',
        requests=REQUESTS
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


@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    return redirect(url_for('login'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
