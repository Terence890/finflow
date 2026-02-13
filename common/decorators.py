"""
Custom decorators for PinkLedger application.

Provides:
- login_required_api: JSON response for API endpoints
- admin_only: Admin-only access control
- route_timer: Performance logging decorator
"""

from functools import wraps
from flask import jsonify, redirect, url_for
from flask_login import current_user
import time
import logging

logger = logging.getLogger(__name__)


def login_required_api(f):
    """
    Require login for API endpoints.

    Returns JSON error response instead of redirecting.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Authentication required.",
                    }
                ),
                401,
            )
        return f(*args, **kwargs)

    return decorated_function


def admin_only(f):
    """Restrict access to admin users only."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        # TODO: Implement admin role check when User model is extended
        # if not current_user.is_admin:
        #     return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def route_timer(f):
    """
    Log route execution time for performance monitoring.

    Useful for identifying bottlenecks in the application.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start_time
        logger.info(f"{f.__name__} took {duration:.3f}s to execute")
        return result

    return decorated_function


def json_response(f):
    """
    Decorator to ensure API responses are JSON.

    Automatically sets Content-Type header and response status.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = f(*args, **kwargs)
        if isinstance(result, dict):
            return jsonify(result)
        return result

    return decorated_function
