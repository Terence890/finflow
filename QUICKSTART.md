"""
Quick Start Guide for PinkLedger (Finflow)

After the enterprise upgrade, here's how to use the project.
"""

# ============================================================================
# INSTALLATION & SETUP
# ============================================================================

# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\Activate.ps1  # Windows PowerShell

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database (one-time)
flask init-db

# 4. Run development server
export FLASK_APP=app.py
flask run

# ============================================================================
# TESTING
# ============================================================================

# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# Run single test
pytest tests/test_auth.py::TestAuthRoutes::test_login_success -v

# ============================================================================
# CODE QUALITY
# ============================================================================

# Format code with black
black .

# Check code style with flake8
flake8 .

# Check types with mypy (optional)
mypy . --ignore-missing-imports

# Run all quality checks
black . && flake8 . && pytest

# ============================================================================
# DATABASE MIGRATIONS
# ============================================================================

# Check current migration status
alembic current

# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# ============================================================================
# USEFUL FILE LOCATIONS
# ============================================================================

# Authentication
auth/model.py       - User model
auth/routes.py      - Login/Register/Logout endpoints
auth/service.py     - Auth business logic
auth/forms.py       - Login & Registration forms

# Finance
finance/models.py   - Income, Expense, Budget models
finance/routes.py   - Dashboard & Finance endpoints
finance/service.py  - Finance business logic
finance/forms.py    - Income, Expense, Budget forms

# Common utilities
common/decorators.py - Reusable decorators (@login_required_api, @route_timer)
common/__init__.py   - Common utilities package

# Testing
tests/conftest.py    - Pytest fixtures and configuration
tests/test_auth.py   - Authentication tests
tests/test_finance.py - Finance tests

# Database
migrations/          - Alembic migration scripts
migrations/env.py    - Alembic environment config
migrations/versions/ - Versioned migration files

# Configuration
config.py            - App configuration
app.py               - Flask app factory
requirements.txt     - Project dependencies

# Frontend
templates/           - HTML templates
static/css/          - Stylesheets (pink theme)
static/js/           - JavaScript (Chart.js, DOM helpers)
static/images/       - Images & assets

# ============================================================================
# COMMON WORKFLOWS
# ============================================================================

# Create new user (via shell)
python - <<'PY'
from app import create_app, db
from auth.model import User
app = create_app()
with app.app_context():
    u = User(name="John", email="john@example.com")
    u.set_password("secure123")
    db.session.add(u)
    db.session.commit()
    print(f"Created user: {u.email}")
PY

# View database contents (SQLite)
sqlite3 instance/database.db
> SELECT * FROM users;
> SELECT * FROM expenses;
> .quit

# Reset database (development only)
rm instance/database.db
flask init-db

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================

# Set Flask environment
export FLASK_ENV=development
export FLASK_DEBUG=1

# Set database URL (optional - uses SQLite by default)
export DATABASE_URL="postgresql://user:password@localhost/pinkledger"

# Set session lifetime (in seconds, default 86400 = 24 hours)
export SESSION_LIFETIME_SECS=604800

# Disable CSRF (not recommended for production)
export WTF_CSRF_ENABLED=0

# ============================================================================
# GITHUB ACTIONS CI/CD
# ============================================================================

# Workflows run automatically on:
# - Push to main/develop branches
# - Pull requests to main/develop branches

# View results in: https://github.com/YOUR_USERNAME/finflow/actions

# Workflows include:
# - tests.yml: pytest, flake8, black, coverage reports
# - quality.yml: pylint, mypy, documentation checks

# ============================================================================
# NEXT STEPS
# ============================================================================

1. Run tests: pytest
2. Try sending a POST to /add-income with JSON data
3. Explore the templates/ directory to customize UI
4. Read migrations/README.md for database management
5. Check GitHub Actions to see CI/CD in action
6. Add your own tests to tests/ directory
7. Deploy using Docker or Gunicorn

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# "No module named 'app'"
# Fix: Ensure you're in the project root directory

# Tests fail with import errors
# Fix: Install dependencies: pip install -r requirements.txt

# Database locked error
# Fix: Close other connections, or delete database.db and reinitialize

# Port 5000 already in use
# Fix: Use: flask run --port 5001

# Form validation errors
# Fix: Check auth/forms.py and finance/forms.py for constraints
