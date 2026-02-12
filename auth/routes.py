from finflow.auth.service import authenticate_user, register_user
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

auth_bp = Blueprint("auth", __name__, template_folder="../templates")


def _get_next_url():
    """Helper to determine redirect target after login/register."""
    next_url = request.args.get("next")
    if next_url:
        return next_url
    return url_for("finance.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Redirect already authenticated users to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("finance.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = authenticate_user(email, password)
        if user:
            login_user(user, remember=remember)
            flash("Logged in successfully.", "success")
            return redirect(_get_next_url())

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("finance.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        # The register template uses 'confirm_password' for the confirmation field.
        confirm = request.form.get("confirm_password", "")

        if not (name and email and password):
            flash("Name, email and password are required.", "warning")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "warning")
            return render_template("register.html")

        user, error = register_user(name=name, email=email, password=password)
        if error:
            flash(error, "danger")
            return render_template("register.html")

        # Auto-login after successful registration
        login_user(user)
        flash("Registration successful \u2014 welcome!", "success")
        return redirect(_get_next_url())

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
