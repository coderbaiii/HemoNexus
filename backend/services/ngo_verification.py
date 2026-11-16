"""
Government Registry Verification & Fraud Detection Engine for Blood Donation NGOs.
Cross-references NGO registration credentials against the official e-RaktKosh (MoHFW) 
dataset and detects fraudulent, disposable, or unauthorized registration attempts.
"""

import os
import json
import re

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "eraktkosh_blood_centers.json")

# Disposable / untrusted email domains
DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "sharklasers.com", "throwawaymail.com", "yopmail.com", "fakeinbox.com",
    "dispostable.com", "trashmail.com", "getairmail.com", "temp-mail.org"
}

# Known fraud / test spam keywords
FRAUD_KEYWORDS = [
    "fraud", "fake", "scam", "phish", "hacker", "dummy_ngo", "test_ngo",
    "illegal", "black_market", "blood_seller", "blood_trafficking"
]

def load_govt_registry():
    """Loads official government e-RaktKosh blood bank registry."""
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def normalize_text(text):
    if not text:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

def verify_ngo_registration(ngo_name, registration_number, email, phone="", city="Kolkata"):
    """
    Evaluates an NGO registration against official government registries and fraud models.
    Returns:
      {
         "is_fraud": bool,
         "fraud_reason": str or None,
         "is_govt_verified": bool,
         "verification_status": "VERIFIED" | "PENDING" | "REJECTED",
         "govt_center_match": dict or None
      }
    """
    clean_name = (ngo_name or "").strip().lower()
    clean_reg = (registration_number or "").strip().upper()
    clean_email = (email or "").strip().lower()
    
    # 1. Check for blatant fraud keywords
    for kw in FRAUD_KEYWORDS:
        if kw in clean_name or kw in clean_reg.lower() or kw in clean_email:
            return {
                "is_fraud": True,
                "fraud_reason": f"Prohibited or fraudulent marker '{kw}' detected in registration credentials.",
                "is_govt_verified": False,
                "verification_status": "REJECTED",
                "govt_center_match": None
            }
            
    # 2. Check disposable email domain
    if "@" in clean_email:
        domain = clean_email.split("@")[1].strip()
        if domain in DISPOSABLE_DOMAINS:
            return {
                "is_fraud": True,
                "fraud_reason": f"Untrusted or disposable email domain '@{domain}' is rejected for healthcare NGOs.",
                "is_govt_verified": False,
                "verification_status": "REJECTED",
                "govt_center_match": None
            }
            
    # 3. Check registration number format
    # Legitimate Indian NGO / Blood Bank numbers follow patterns like WB-NGO-*, DL-NGO-*, NGO-*, BB-*, eRK-*
    reg_clean_norm = re.sub(r'[^A-Z0-9]', '', clean_reg)
    if len(reg_clean_norm) < 4 or reg_clean_norm in ("0000", "1234", "12345", "123456", "FAKE"):
        return {
            "is_fraud": True,
            "fraud_reason": f"Invalid or synthetic registration number format '{clean_reg}'.",
            "is_govt_verified": False,
            "verification_status": "REJECTED",
            "govt_center_match": None
        }

    # 4. Cross-reference against official e-RaktKosh Government Blood Centers Dataset
    govt_centers = load_govt_registry()
    matched_center = None
    
    # Pre-authorized recognized NGO organizations
    recognized_patterns = [
        "red cross", "indian red cross", "lions club", "lions blood",
        "rotary", "jeevandeep", "hope youth", "lifesavers",
        "calcutta national medical", "esi blood centre", "dr. b.c. roy"
    ]
    
    is_recognized = any(pat in clean_name for pat in recognized_patterns)
    
    for center in govt_centers:
        center_name = center.get("name", "").lower()
        # Direct name match or substring match
        if clean_name and (clean_name in center_name or center_name in clean_name):
            matched_center = center
            break
            
    if matched_center or is_recognized:
        return {
            "is_fraud": False,
            "fraud_reason": None,
            "is_govt_verified": True,
            "verification_status": "VERIFIED",
            "govt_center_match": matched_center or {"name": ngo_name, "source": "Official Healthcare Registry"}
        }

    return {
        "is_fraud": False,
        "fraud_reason": None,
        "is_govt_verified": False,
        "verification_status": "PENDING",
        "govt_center_match": None
    }
