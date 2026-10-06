import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "hemonexus-smart-blood-donor-secret-key-2026")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "hemonexus.db"))
    
    # Six-Month Verification Settings
    VERIFICATION_INTERVAL_DAYS = int(os.environ.get("VERIFICATION_INTERVAL_DAYS", "180"))  # 6 months (~180 days)
    GRACE_PERIOD_DAYS = int(os.environ.get("GRACE_PERIOD_DAYS", "30"))                    # 30 days grace period
    
    # Donation Cooldown Settings (Operational Search Prioritization)
    # Default 56 days for whole blood donation spacing in this prototype.
    # NOTE: Software does NOT determine medical eligibility. Actual donor deferral intervals
    # must be established and authorized by the blood centre / medical officer.
    DEFAULT_DONATION_COOLDOWN_DAYS = int(os.environ.get("DONATION_COOLDOWN_DAYS", "56"))

    # Matching defaults
    DEFAULT_MAX_DISTANCE_KM = float(os.environ.get("DEFAULT_MAX_DISTANCE_KM", "25.0"))
    DEFAULT_AVERAGE_SPEED_KMH = float(os.environ.get("DEFAULT_AVERAGE_SPEED_KMH", "30.0")) # Configurable average city speed
    
    # Transparent Ranking Weights for "BEST MATCH" (Summing to 1.0)
    WEIGHT_AVAILABILITY = float(os.environ.get("WEIGHT_AVAILABILITY", "0.35"))
    WEIGHT_DISTANCE = float(os.environ.get("WEIGHT_DISTANCE", "0.40"))
    WEIGHT_FRESHNESS = float(os.environ.get("WEIGHT_FRESHNESS", "0.25"))
    WEIGHT_PROXIMITY_FIT = 0.0  # Merged into WEIGHT_DISTANCE to prevent double counting
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production

class TestConfig(Config):
    TESTING = True
    DATABASE_PATH = ":memory:"
