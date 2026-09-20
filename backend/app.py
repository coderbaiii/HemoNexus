import sys
from pathlib import Path

# Add project root to sys.path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
from flask import Flask, jsonify, request, render_template
from backend.config import Config
from backend.database import close_db
from backend.init_db import init_database
from backend.routes.auth import auth_bp
from backend.routes.donor import donor_bp
from backend.routes.patient import patient_bp
from backend.routes.admin import admin_bp
from backend.routes.web import web_bp

def create_app(config_class=Config):
    """
    Application factory for HEMONEXAS Flask platform.
    """
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent / "static")
    )
    app.config.from_object(config_class)

    # Teardown database connection
    app.teardown_appcontext(close_db)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(donor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(web_bp)

    # Ensure database schema is initialized if file doesn't exist
    if app.config.get("DATABASE_PATH") and app.config["DATABASE_PATH"] != ":memory:":
        db_path = Path(app.config["DATABASE_PATH"])
        if not db_path.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with app.app_context():
                init_database(str(db_path), seed_demo=True)

    # API Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Bad Request: " + str(getattr(e, 'description', e))}), 400
        return "Bad Request", 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Unauthorized: Authentication required."}), 401
        return "Unauthorized", 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Forbidden: Insufficient privileges."}), 403
        return "Forbidden", 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Resource not found."}), 404
        return "Page Not Found", 404

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
