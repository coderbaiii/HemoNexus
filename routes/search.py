"""
HEMONEXAS Search Blueprint
Handles interactive requirement-based donor search and filtering.
"""
from flask import Blueprint, request, jsonify, render_template, session
from database.db import get_db, query_db
from matching.matcher import run_matching_pipeline

search_bp = Blueprint("search", __name__)

VALID_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
VALID_SORTS = ("NEAREST", "FASTEST", "RECENTLY_VERIFIED", "BEST_MATCH")

@search_bp.route("/search")
def search_page():
    """Renders the dedicated interactive donor search portal."""
    return render_template("search.html")

@search_bp.route("/api/search/donors", methods=["POST", "GET"])
def search_donors():
    """
    Executes the 10-step requirement-based donor search with custom filters:
    - Blood group (Required)
    - Latitude & Longitude (Patient/Hospital coordinates)
    - Search distance radius (km)
    - Availability preference (24_HOURS, DAY, NIGHT, 8_HOURS, ANY)
    - Sorting preference (NEAREST, FASTEST, RECENTLY_VERIFIED, BEST_MATCH)
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
    else:
        data = request.args.to_dict()

    blood_group = (data.get("blood_group") or "").strip().upper()
    if not blood_group or blood_group not in VALID_BLOOD_GROUPS:
        return jsonify({"success": False, "error": f"Valid blood group required ({', '.join(VALID_BLOOD_GROUPS)})."}), 400

    try:
        max_dist = float(data.get("preferred_max_distance") or 25.0)
    except (ValueError, TypeError):
        max_dist = 25.0

    lat = data.get("latitude")
    lon = data.get("longitude")
    try:
        lat = float(lat) if lat is not None and lat != "" else 22.5697  # Default Kolkata center
        lon = float(lon) if lon is not None and lon != "" else 88.4046
    except (ValueError, TypeError):
        lat = 22.5697
        lon = 88.4046

    sort_pref = (data.get("sorting_preference") or "BEST_MATCH").strip().upper()
    if sort_pref not in VALID_SORTS:
        sort_pref = "BEST_MATCH"

    avail_pref = (data.get("availability_preference") or "ANY").strip().upper()
    urgency = (data.get("urgency") or "NORMAL").strip().upper()

    conn = get_db()
    sql = """
        SELECT d.id AS donor_id, d.user_id, d.blood_group, d.phone, d.location,
               d.latitude, d.longitude, d.availability, d.available_from, d.available_to,
               d.maximum_travel_distance, d.is_available, d.profile_status,
               d.last_verified_date, d.next_verification_date,
               u.full_name, u.email
        FROM donor_profiles d
        JOIN users u ON d.user_id = u.id
    """
    raw_donors = query_db(sql, db=conn)

    request_spec = {
        "required_blood_group": blood_group,
        "latitude": lat,
        "longitude": lon,
        "preferred_max_distance": max_dist,
        "urgency": urgency,
        "sorting_preference": sort_pref
    }

    results = run_matching_pipeline(request_spec, raw_donors, sorting_preference=sort_pref)

    # Optional availability preference post-filter if specific type requested
    if avail_pref != "ANY":
        norm_pref = avail_pref.replace(" ", "_")
        results = [r for r in results if (r.get("availability") or "").upper().replace(" ", "_") == norm_pref]

    return jsonify({
        "success": True,
        "total_matches": len(results),
        "results": results,
        "filters_applied": {
            "blood_group": blood_group,
            "max_distance_km": max_dist,
            "sorting_preference": sort_pref,
            "availability_preference": avail_pref,
            "patient_latitude": lat,
            "patient_longitude": lon
        }
    }), 200
