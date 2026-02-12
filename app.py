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
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user

# Extensions (single instances to be imported elsewhere if needed)
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(test_config: dict | None = None) -> Flask:
    """
    Application factory - creates and configures the Flask app.
    Accepts optional test_config for easier testing.
    """
    app = Flask(__name__, instance_relative_config=False)

    # Basic configuration - can be overridden by test_config or instance config
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///database.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Register blueprints (optional imports to avoid circular imports)
    try:
        from auth.routes import auth_bp  # type: ignore
        app.register_blueprint(auth_bp, url_prefix="/auth")
    except Exception:
        # Blueprint may not exist yet during early development; skip if missing.
        pass

    try:
        from finance.routes import finance_bp  # type: ignore
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
            db.create_all()
            print("Initialized the database.")

    return app


# When run directly, start the development server (use create_app for production/factory pattern)
if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, host="127.0.0.1", port=5000)
