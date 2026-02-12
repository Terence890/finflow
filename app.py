"""
Entrypoint for PinkLedger (Finflow) Flask application.

Responsibilities:
- Create and configure the Flask app
- Initialize extensions (SQLAlchemy, LoginManager)
- Register blueprints (auth, finance)
- Provide a small CLI helper to initialize the database

This file is intentionally small and focused on app setup (keeps single responsibility).
"""

import os
import sys

# Ensure the parent directory is in PYTHONPATH so finflow package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Alias this module to avoid duplicate imports between app and finflow.app
if "finflow.app" not in sys.modules:
    sys.modules["finflow.app"] = sys.modules[__name__]

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy

# Extensions (single instances to be imported elsewhere if needed)
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(test_config: dict | None = None) -> Flask:
    """
    Application factory - creates and configures the Flask app.
    Accepts optional test_config for easier testing.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance folder exists for SQLite DB and instance config
    os.makedirs(app.instance_path, exist_ok=True)

    # Basic configuration - can be overridden by test_config or instance config
    default_db_path = os.path.join(app.instance_path, "database.db")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{default_db_path}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Register user_loader callback for Flask-Login
    # This must be done before importing modules that use current_user
    @login_manager.user_loader
    def load_user(user_id: str):
        """Load user by ID for Flask-Login."""
        from finflow.auth.model import User

        if not user_id:
            return None
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return None
        return User.query.get(uid)

    # Register blueprints using package-style imports to avoid ambiguity.
    try:
        from finflow.auth.routes import auth_bp  # type: ignore

        app.register_blueprint(auth_bp, url_prefix="/auth")
    except Exception:
        # Blueprint may not exist yet during early development; skip if missing.
        pass

    try:
        from finflow.finance.routes import finance_bp  # type: ignore

        app.register_blueprint(finance_bp, url_prefix="/finance")
    except Exception:
        # Same as above
        pass

    # Simple index route -> redirect to dashboard or login
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("finance.dashboard"))
        return redirect(url_for("auth.login"))

    # CLI command to initialize the database
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables."""
        with app.app_context():
            # Import models so SQLAlchemy registers tables before create_all
            from finflow.auth import model  # noqa: F401
            from finflow.finance import models  # noqa: F401
            db.create_all()
            print("Initialized the database.")

    return app


# When run directly, start the development server (use create_app for production/factory pattern)
if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, host="127.0.0.1", port=5000)
