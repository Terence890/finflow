# PinkLedger (Finflow)

A lightweight, modular financial management mini-project built with Flask, designed for learning and easy extension. The codebase follows a clean, human-friendly structure with small files (aim ≤ 100 lines) and a pastel "girly pink" UI theme.

---

## Quick summary

- Framework: Flask (application factory pattern)
- ORM: SQLAlchemy
- Auth: Flask-Login
- DB: SQLite (default `database.db`)
- Frontend: Server-rendered Jinja templates + small vanilla JS + Chart.js
- Goal: Readable, modular code suitable for learning and demonstration

---

## Table of contents

1. Project layout
2. Setup (local)
3. Development workflow
4. Key design principles
5. Files & responsibilities
6. Common tasks
7. Extending the project
8. Testing & linting
9. Troubleshooting
10. License & credits

---

## 1) Project layout (high-level)

Finflow/
- `app.py` - application factory and extension initialization
- `config.py` - centralized configuration (env-driven)
- `database.db` - default SQLite DB (created at runtime)
- `auth/`
  - `model.py` - `User` model and login loader
  - `service.py` - registration & authentication logic
  - `routes.py` - auth blueprint (login/register/logout)
- `finance/`
  - `models.py` - `Income`, `Expense`, `Budget` models
  - `routes.py` - finance blueprint (dashboard + API endpoints)
- `templates/` - Jinja2 templates (`base.html`, `login.html`, `register.html`, `dashboard.html`, ...)
- `static/`
  - `css/style.css` - theme & layout
  - `js/main.js` - small UI helpers
- `README.md` - this document

Each file focuses on one responsibility and aims to be compact and human readable.

---

## 2) Setup (local)

Prerequisites:
- Python 3.10+
- Git (optional)
- (Optional) Node/npm for frontend toolchain if you add one

Recommended steps:

1. Create and activate a virtual environment
   - Unix / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```

2. Install dependencies
   (If you don't have a `requirements.txt`, install minimal deps:)
   ```
   pip install Flask Flask-Login Flask-SQLAlchemy Werkzeug
   ```

3. Set environment variables and run
   - Unix:
     ```
     export FLASK_APP="Finflow.app:create_app"
     export FLASK_ENV=development
     flask init-db
     flask run --host=127.0.0.1 --port=5000
     ```
   - Windows (PowerShell):
     ```
     $env:FLASK_APP = 'Finflow.app:create_app'
     $env:FLASK_ENV = 'development'
     flask init-db
     flask run
     ```

4. Open the app: http://127.0.0.1:5000

Notes:
- `flask init-db` runs a small CLI helper registered in `app.py` to create tables.
- The first time you run, the SQLite file `database.db` will be created in the project directory.

---

## 3) Development workflow

- Use the application factory `create_app()` in `app.py` so you can pass test configs in unit tests.
- Keep file responsibilities narrow:
  - `routes.py` only defines endpoints and request/response flow.
  - `service.py` contains business logic and DB transactions.
  - `model.py` contains the SQLAlchemy models and helper methods.
- Aim to keep each module under ~100 lines for clarity and to match the learning goal.

Example quick iteration:
- Edit a route or template
- Restart the dev server (or use Flask's auto-reload)
- Test behavior in browser

---

## 4) Key design principles (follow for all future changes)

- Single responsibility per file
- Small functions (readable & testable)
- Explicit and descriptive names
- Keep templates simple and reuse blocks (base.html)
- Avoid business logic inside templates or routes — put logic in service layer
- Add comments for non-obvious decisions

---

## 5) Files & responsibilities (detailed)

- `app.py`
  - Creates the Flask app, initializes `SQLAlchemy` and `LoginManager`.
  - Registers blueprints and provides `flask` CLI helper `init-db`.
- `config.py`
  - Centralized configuration values. Read environment variables here for production overrides.
- `auth/model.py`
  - `User` class: password hashing helpers, `to_dict`, and `user_loader`.
- `auth/service.py`
  - `register_user()`, `authenticate_user()`, `get_user_by_email()` — returns clear (value, error) patterns for easy handling in routes.
- `auth/routes.py`
  - `auth_bp` blueprint with `/login`, `/register`, `/logout`.
  - Handles form validation at a minimal level and uses `service` functions.
- `finance/models.py`
  - `Income`, `Expense`, `Budget` models. Each includes `to_dict()` for APIs.
- `finance/routes.py`
  - `finance_bp` blueprint with dashboard, JSON endpoints for income/expense CRUD, and summary endpoints consumed by Chart.js.
- `templates/`
  - `base.html` - site skeleton with nav and blocks.
  - `login.html`, `register.html`, `dashboard.html` - important pages for initial functionality.
- `static/`
  - CSS and JS for a small, pretty, responsive UI.

---

## 6) Common tasks

Create an initial user (quick):
- Use Python shell to create a user if you don't want to register via UI:
  ```
  python - <<'PY'
  from Finflow.app import create_app, db
  from Finflow.auth.model import User
  app = create_app()
  with app.app_context():
      u = User(name="Admin", email="admin@example.com")
      u.set_password("password123")
      db.session.add(u)
      db.session.commit()
      print("Created user", u.email)
  PY
  ```

Export CSV (example idea):
- Implement an endpoint that queries the DB and returns `text/csv` with headers. Use Python's `csv` module to stream rows.

Enable CSRF:
- Install `Flask-WTF` and wrap forms with `FlaskForm` or add `WTF_CSRF_ENABLED` in `config.py`. Templates already have placeholders to include CSRF tokens.

Add Docker:
- You can add a simple Dockerfile that installs python, copies files, installs pip deps, and runs `flask run`. If you want, I can add a sample Dockerfile and docker-compose.

---

## 7) Extending the project

Suggested next features (pick one):
- CSV export & PDF reports (use `reportlab` or `weasyprint` / `wkhtmltopdf`)
- Add unit tests with `pytest` covering `auth/service.py` and `finance/routes.py` (API-level)
- Add pagination endpoints for large lists
- Introduce Flask-Migrate for migrations
- Add role-based access (admin vs user) if multi-tenant features are needed
- Connect to a real DB (Postgres) for production

---

## 8) Testing & linting

- Add `pytest` and write tests for services and small route behaviors using Flask's `test_client()`.
- Use `flake8` / `black` / `isort` for consistent style:
  ```
  pip install pytest flake8 black isort
  black Finflow
  flake8 Finflow
  ```

---

## 9) Troubleshooting

- "Module not found" for `Finflow.*`: ensure `FLASK_APP` is set to `Finflow.app:create_app` and you're running the command from the project parent directory.
- DB errors on table creation: delete `database.db` and re-run `flask init-db` in dev (only for local dev; be careful in production).
- Login not working: confirm `User` table has a `password_hash` and that `Flask-Login` is correctly initialized in `app.py`.

---

## 10) Notes, conventions & tips

- Keep templates small and prefer blocks + macros in `base.html`.
- Keep SQLAlchemy models explicit about column types and constraints.
- Prefer JSON API endpoints for programmatic access and server-rendered templates for simple UI flows.
- When adding new files, follow the single-responsibility pattern (one file, one concept).
- Document any breaking changes in the README.

---

## License & credits

This project was built for learning and demonstration. Feel free to fork and adapt for personal or academic projects.

If you'd like, I can:
- create a `requirements.txt`
- add Docker configuration
- add a `Makefile` with common tasks
- add unit tests

Tell me which of these you'd like next and I'll produce the files.