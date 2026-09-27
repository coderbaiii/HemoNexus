"""
HEMONEXAS AI Help Assistant & FAQ Engine
Provides an interactive help assistant to guide users through platform operations.
Features strict medical boundary guardrails: will refuse medical diagnoses, disease predictions,
or clinical transfusion advice.
"""
from flask import Blueprint, request, jsonify

chatbot_bp = Blueprint("chatbot", __name__)

MEDICAL_KEYWORDS = [
    "hiv", "hepatitis", "disease", "diagnosis", "infection", "cancer", "malaria",
    "syphilis", "diabetes", "transfusion reaction", "compatibility test", "medical fitness",
    "can i donate if i have", "blood test", "medicine", "pregnant", "blood safety"
]

MEDICAL_SAFETY_RESPONSE = (
    "⚠️ **Medical Safety Policy**: HEMONEXAS is an operational donor management and requirement-based "
    "matching platform. It is **NOT** a medical diagnostic tool and does **NOT** make medical eligibility "
    "or transfusion compatibility decisions. All donor health assessments, infectious disease screenings "
    "(such as HIV, Hepatitis B/C), and final transfusion approvals are conducted strictly by authorized medical "
    "personnel at a licensed blood center."
)

FAQ_KNOWLEDGE_BASE = [
    {
        "keywords": ["register", "sign up", "create account", "join"],
        "answer": (
            "**How to Register on HEMONEXAS:**\n"
            "1. Click the **Register** button in the top navigation.\n"
            "2. Select your role: **Blood Donor** or **Patient / Hospital Requester**.\n"
            "3. Enter your full name, email, and secure password.\n"
            "4. Donors can also enter their blood group, location, availability window, and maximum travel radius.\n"
            "5. Once submitted, your profile is immediately initialized!"
        )
    },
    {
        "keywords": ["blood request", "post request", "need blood", "create request", "patient request"],
        "answer": (
            "**How to Create a Blood Request:**\n"
            "1. Sign in with your Patient account and navigate to the **Patient Dashboard**.\n"
            "2. Under **New Blood Requirement**, choose the required blood group and number of units.\n"
            "3. Enter the hospital name, location, and GPS coordinates (optional or auto-filled).\n"
            "4. Choose your urgency level (Normal, Urgent, Critical) and preferred search radius.\n"
            "5. Click **Publish Blood Request & Match Donors** to instantly run the 10-step matching engine!"
        )
    },
    {
        "keywords": ["matching", "algorithm", "how it works", "ranking", "filter", "score"],
        "answer": (
            "**How the 10-Step Requirement-Based Matching Works:**\n"
            "1. **Blood Group Filter**: Only donors matching the exact required blood group pass.\n"
            "2. **Active Status**: Profiles must be currently ACTIVE.\n"
            "3. **6-Month Verification**: Donors with expired verification due dates are excluded.\n"
            "4. **Temporary Availability**: Donors who set themselves unavailable are pruned.\n"
            "5. **Availability Schedule**: Donors must be available during the requested time window.\n"
            "6. **Haversine Distance**: Computes great-circle distance (km) without third-party APIs.\n"
            "7. **Patient Radius**: Distance must not exceed patient's requested maximum.\n"
            "8. **Donor Travel Limit**: Distance must not exceed donor's willingness to travel.\n"
            "9. **Candidate List**: Only donors satisfying all conditions proceed to ranking.\n"
            "10. **Ranking**: Candidates are sorted by Nearest, Fastest, Recently Verified, or Best Match!"
        )
    },
    {
        "keywords": ["verification", "6 month", "six month", "verify profile", "due", "inactive", "renew"],
        "answer": (
            "**How the 6-Month Verification Cycle Works:**\n"
            "• Every donor profile has a `last_verified_date` and a `next_verification_date` (180 days apart).\n"
            "• **Verified / ACTIVE**: When your profile is within the 180-day cycle.\n"
            "• **Verification Due**: When 180 days pass, you enter a 30-day grace period.\n"
            "• **INACTIVE**: If not re-confirmed within the grace period, your profile becomes inactive.\n"
            "• **How to Re-activate**: Click the **Confirm Profile Freshness** button on your Donor Dashboard at any time to reset your 6-month cycle to ACTIVE!"
        )
    },
    {
        "keywords": ["availability", "schedule", "travel distance", "night", "day", "unavailable"],
        "answer": (
            "**How to Update Availability & Travel Limits:**\n"
            "1. Log into your **Donor Dashboard**.\n"
            "2. Choose your schedule pattern: **24 Hours**, **Daytime (08:00–18:00)**, **Nighttime (18:00–06:00)**, or **8-Hour Shift (09:00–17:00)**.\n"
            "3. Set your **Maximum Travel Distance** (e.g., 15 km).\n"
            "4. Toggle **Temporary Availability** if you are temporarily ill, traveling, or unable to donate.\n"
            "5. Click **Save Profile Updates**."
        )
    },
    {
        "keywords": ["navigate", "where is", "how do i", "menu", "admin", "contact"],
        "answer": (
            "**Platform Navigation Guide:**\n"
            "• **Home**: Overview of HEMONEXAS and emergency donor search.\n"
            "• **Donor Dashboard**: Manage your verification cycle, availability, and respond to incoming requests.\n"
            "• **Patient Dashboard**: Post blood requirements and inspect matching donors.\n"
            "• **Search Page**: Search verified donors anytime with custom filters.\n"
            "• **Admin Console**: Monitored view of donor statuses, requests, and blood bank records."
        )
    }
]

@chatbot_bp.route("/api/chatbot/ask", methods=["POST"])
def ask_chatbot():
    """
    Evaluates user message and returns a helpful operational response.
    Includes automated medical disclaimer guardrails.
    """
    data = request.get_json(silent=True) or request.form.to_dict()
    query = (data.get("message") or "").strip().lower()

    if not query:
        return jsonify({"success": False, "error": "Query message cannot be empty."}), 400

    # 1. Check Medical Guardrail Trigger
    for kw in MEDICAL_KEYWORDS:
        if kw in query:
            return jsonify({
                "success": True,
                "answer": MEDICAL_SAFETY_RESPONSE,
                "is_medical_refusal": True
            }), 200

    # 2. Check FAQ Knowledge Base
    best_match = None
    max_hits = 0
    for item in FAQ_KNOWLEDGE_BASE:
        hits = sum(1 for kw in item["keywords"] if kw in query)
        if hits > max_hits:
            max_hits = hits
            best_match = item["answer"]

    if best_match and max_hits > 0:
        return jsonify({
            "success": True,
            "answer": best_match,
            "is_medical_refusal": False
        }), 200

    # 3. Default Fallback
    fallback_response = (
        "Hello! I am your **HEMONEXAS Guide Assistant**. I can help you with:\n"
        "• How to register as a donor or patient\n"
        "• How to create an emergency blood request\n"
        "• How the 10-step requirement matching engine works\n"
        "• Updating donor availability & travel distance limits\n"
        "• The 6-month profile verification lifecycle\n\n"
        "*Please type a question about any of these topics, or consult your hospital or local blood bank for medical health screening inquiries.*"
    )
    return jsonify({
        "success": True,
        "answer": fallback_response,
        "is_medical_refusal": False
    }), 200
