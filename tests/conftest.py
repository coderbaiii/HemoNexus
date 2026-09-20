import os
import tempfile
import pytest
from backend.app import create_app
from backend.config import Config
from backend.init_db import init_database
from backend.database import get_db

@pytest.fixture
def test_db_path():
    """Create a unique temporary database file for the test session."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass

@pytest.fixture
def app(test_db_path):
    """Flask application configured for testing with an isolated database."""
    class TestAppConfig(Config):
        TESTING = True
        DATABASE_PATH = test_db_path
        SECRET_KEY = "test-secret-key"

    app = create_app(TestAppConfig)
    with app.app_context():
        init_database(test_db_path, seed_demo=True)
    yield app

@pytest.fixture
def client(app):
    """Test client for unauthenticated HTTP requests."""
    return app.test_client()

@pytest.fixture
def db_conn(app, test_db_path):
    """Direct database connection to the test database."""
    with app.app_context():
        conn = get_db(test_db_path)
        yield conn

@pytest.fixture
def admin_client(app):
    """Dedicated test client authenticated as administrator."""
    c = app.test_client()
    c.post("/api/login", json={
        "email": "admin@hemonexus.org",
        "password": "Admin@123456"
    })
    return c

@pytest.fixture
def donor_client(app):
    """Dedicated test client authenticated as donor (Amitav Sengupta, O+)."""
    c = app.test_client()
    c.post("/api/login", json={
        "email": "amitav.donor@example.com",
        "password": "Donor@1234"
    })
    return c

@pytest.fixture
def patient_client(app):
    """Dedicated test client authenticated as patient (Rajesh Kumar)."""
    c = app.test_client()
    c.post("/api/login", json={
        "email": "patient.raj@example.com",
        "password": "Patient@1234"
    })
    return c
