"""
Authentication forms with built-in validation.

Forms:
- LoginForm: Email and password validation
- RegisterForm: Name, email, password confirmation validation

Uses Flask-WTF for CSRF protection and validation.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from auth.model import User


class LoginForm(FlaskForm):
    """Login form with email and password fields."""

    email = StringField(
        "Email",
        validators=[
            DataRequired("Email is required."),
            Email("Invalid email address."),
        ],
    )
    password = PasswordField(
        "Password", validators=[DataRequired("Password is required.")]
    )
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign In")


class RegisterForm(FlaskForm):
    """Registration form with name, email, and password fields."""

    name = StringField(
        "Full Name",
        validators=[
            DataRequired("Name is required."),
            Length(min=3, max=100, message="Name must be 3-100 characters."),
        ],
    )
    email = StringField(
        "Email",
        validators=[
            DataRequired("Email is required."),
            Email("Invalid email address."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired("Password is required."),
            Length(min=6, message="Password must be at least 6 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired("Password confirmation is required."),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Create Account")

    def validate_email(self, email):
        """Check if email already exists."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email already registered.")
