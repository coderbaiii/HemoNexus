"""
HemoNexus - Smart Blood Donor Management & Requirement-Based Matching System
Flask Application Entry Point
"""

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

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
        "city": "Mumbai",
        "area": "Andheri West",
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
        "city": "Mumbai",
        "area": "Bandra West",
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
        "city": "Mumbai",
        "area": "Powai",
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
        "city": "Mumbai",
        "area": "Dadar",
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
        "area": "Juhu",
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
        "city": "Mumbai",
        "area": "Goregaon",
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
        "hospital": "Lilavati Hospital & Research Centre",
        "location": "Bandra, Mumbai",
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
        "hospital": "Tata Memorial Hospital",
        "location": "Parel, Mumbai",
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
        "hospital": "Kokilaben Dhirubhai Ambani Hospital",
        "location": "Andheri West, Mumbai",
        "urgency": "routine",
        "status": "fulfilled",
        "requiredBy": "2026-08-27 02:00 PM",
        "createdAt": "14:00 PM",
        "contactPhone": "+91 98333 44556"
    }
]

ACTIVITIES = [
    {
        "title": "Donor Dispatch Confirmed",
        "desc": "Aarav Sharma accepted emergency request REQ-4091 for Lilavati Hospital.",
        "time": "12 mins ago",
        "icon": "fa-truck-medical",
        "iconClass": "stat-icon-primary"
    },
    {
        "title": "New Blood Request Registered",
        "desc": "Emergency O- Whole Blood request logged by Lilavati ICU.",
        "time": "45 mins ago",
        "icon": "fa-droplet",
        "iconClass": "stat-icon-danger"
    },
    {
        "title": "Donation Completed & Verified",
        "desc": "Devendra Joshi request fulfilled with 2 units of B+ RBC.",
        "time": "2 hours ago",
        "icon": "fa-circle-check",
        "iconClass": "stat-icon-success"
    }
]


@app.route('/')
def index():
    # Site opens directly to Login page as the first view
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('userRole', 'donor')
        # Redirect to operations dashboard or home after successful authentication
        return redirect(url_for('dashboard'))
    role = request.args.get('role', 'donor')
    return render_template('login.html', is_public_page=True, active_page='login', active_role=role)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return redirect(url_for('dashboard'))
    role = request.args.get('role', 'donor')
    return render_template('register.html', is_public_page=True, active_page='register', active_role=role)


@app.route('/home')
@app.route('/landing')
def home():
    # Main product homepage after login or via navigation
    return render_template('home.html', is_public_page=True, active_page='home')


@app.route('/dashboard')
def dashboard():
    return render_template(
        'dashboard.html',
        is_public_page=False,
        active_page='dashboard',
        donors=DONORS,
        requests=REQUESTS,
        activities=ACTIVITIES
    )


@app.route('/donors')
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
def matching():
    pre_group = request.args.get('group', 'O-')
    pre_comp = request.args.get('component', 'Whole Blood')
    return render_template(
        'matching.html',
        is_public_page=False,
        active_page='match',
        pre_group=pre_group,
        pre_comp=pre_comp
    )


@app.route('/emergency')
def emergency():
    return render_template(
        'emergency.html',
        is_public_page=False,
        active_page='emergency'
    )


@app.route('/availability')
def availability():
    return render_template(
        'availability.html',
        is_public_page=False,
        active_page='availability'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
