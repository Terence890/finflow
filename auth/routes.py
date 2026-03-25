from finflow.auth.service import authenticate_user, register_user
from finflow.auth.forms import LoginForm, RegisterForm
from finflow.common.logger import auth_logger, log_auth_event
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

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip()
        password = form.password.data
        remember = bool(form.remember.data)

        user = authenticate_user(email, password)
        if user:
            login_user(user, remember=remember)
            log_auth_event("login", user_id=user.id, email=user.email, status="success")
            flash("Logged in successfully.", "success")
            return redirect(_get_next_url())

        log_auth_event("login", email=email, status="failed")
        flash("Invalid email or password.", "danger")
    elif request.method == "POST":
        flash("Please correct the form errors and try again.", "warning")
        auth_logger.warning("Login form validation failed")

    return render_template("login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("finance.dashboard"))

    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data.strip()
        email = form.email.data.strip()
        password = form.password.data

        user, error = register_user(name=name, email=email, password=password)
        if error:
            log_auth_event("register", email=email, status="failed")
            flash(error, "danger")
            return render_template("register.html", form=form)

        # Auto-login after successful registration
        login_user(user)
        log_auth_event("register", user_id=user.id, email=user.email, status="success")
        flash("Registration successful - welcome!", "success")
        return redirect(_get_next_url())
    elif request.method == "POST":
        flash("Please correct the form errors and try again.", "warning")
        auth_logger.warning("Registration form validation failed")

    return render_template("register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_auth_event(
        "logout",
        user_id=current_user.id,
        email=getattr(current_user, "email", None),
        status="success",
    )
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
