import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "hemonexus-smart-blood-donor-secret-key-2026")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "hemonexus.db"))
    
    # Six-Month Verification Settings
    VERIFICATION_INTERVAL_DAYS = int(os.environ.get("VERIFICATION_INTERVAL_DAYS", "180"))  # 6 months (~180 days)
    GRACE_PERIOD_DAYS = int(os.environ.get("GRACE_PERIOD_DAYS", "30"))                    # 30 days grace period
    
    # Matching defaults
    DEFAULT_MAX_DISTANCE_KM = 25.0
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production

class TestConfig(Config):
    TESTING = True
    DATABASE_PATH = ":memory:"
