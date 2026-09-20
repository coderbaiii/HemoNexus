from flask import Blueprint, render_template, session, redirect, url_for

web_bp = Blueprint("web", __name__)

@web_bp.route("/")
def index():
    return render_template("index.html")

@web_bp.route("/login")
def login_page():
    if "user_id" in session:
        role = session.get("role")
        if role == "donor":
            return redirect(url_for("web.donor_dashboard"))
        elif role == "patient":
            return redirect(url_for("web.patient_dashboard"))
        elif role == "admin":
            return redirect(url_for("web.admin_dashboard"))
    return render_template("login.html")

@web_bp.route("/register")
def register_page():
    if "user_id" in session:
        return redirect(url_for("web.index"))
    return render_template("register.html")

@web_bp.route("/donor/dashboard")
def donor_dashboard():
    if "user_id" not in session:
        return redirect(url_for("web.login_page"))
    if session.get("role") not in ("donor", "admin"):
        return redirect(url_for("web.index"))
    return render_template("donor_dashboard.html")

@web_bp.route("/patient/dashboard")
def patient_dashboard():
    if "user_id" not in session:
        return redirect(url_for("web.login_page"))
    if session.get("role") not in ("patient", "admin"):
        return redirect(url_for("web.index"))
    return render_template("patient_dashboard.html")

@web_bp.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("web.login_page"))
    return render_template("admin_dashboard.html")
