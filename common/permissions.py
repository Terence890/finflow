"""
Permission and authorization utilities for PinkLedger (Finflow).

Provides:
- Permission decorators
- Access control helpers
- Data ownership validation
"""

from functools import wraps
from typing import Any, Callable, Optional, Type

from flask import jsonify, redirect, url_for, abort, request
from flask_login import current_user

from finflow.common.logger import log_permission_error


def require_owned_by_user(
    model_class: Type[Any], id_param: str = "item_id", user_id_attr: str = "user_id"
) -> Callable:
    """
    Decorator to ensure current user owns the resource.

    Validates that the resource identified by id_param belongs to current_user.

    Args:
        model_class: SQLAlchemy model class to query
        id_param: Name of URL parameter containing resource ID
        user_id_attr: Name of user_id attribute on model

    Returns:
        Decorated function

    Example:
        @require_owned_by_user(Income, "item_id")
        def delete_income(item_id):
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resource_id = kwargs.get(id_param)
            if not resource_id:
                abort(400, "Resource ID required")

            resource = model_class.query.get_or_404(resource_id)
            resource_owner_id = getattr(resource, user_id_attr, None)

            if resource_owner_id != current_user.id:
                log_permission_error(
                    current_user.id,
                    model_class.__name__.lower(),
                    resource_id,
                    action="access",
                )
                if request.is_json:
                    return jsonify({"error": "Forbidden"}), 403
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_user_owns_data(model: Any, user_id_attr: str = "user_id") -> bool:
    """
    Check if current user owns a data model instance.

    Args:
        model: Model instance to check
        user_id_attr: Name of user_id attribute

    Returns:
        True if user owns the data, False otherwise
    """
    if not current_user.is_authenticated:
        return False

    model_owner_id = getattr(model, user_id_attr, None)
    return model_owner_id == current_user.id


def ensure_user_owns_data(
    model: Any, user_id_attr: str = "user_id", raise_error: bool = True
) -> bool:
    """
    Ensure current user owns a data model instance.

    Args:
        model: Model instance to check
        user_id_attr: Name of user_id attribute
        raise_error: If True, abort on unauthorized; if False, return False

    Returns:
        True if user owns the data

    Raises:
        403 if raise_error is True and user doesn't own data
    """
    owns_data = check_user_owns_data(model, user_id_attr)

    if not owns_data and raise_error:
        log_permission_error(
            current_user.id if current_user.is_authenticated else 0,
            model.__class__.__name__.lower(),
            getattr(model, "id", None),
            action="access",
        )
        abort(403, "You don't have permission to access this resource")

    return owns_data


def validate_user_context(user_id: int, raise_error: bool = True) -> bool:
    """
    Validate that the given user_id matches the current user.

    Useful for validating that queries are for the current user only.

    Args:
        user_id: User ID to validate against current user
        raise_error: If True, abort on mismatch; if False, return False

    Returns:
        True if user_id matches current user

    Raises:
        403 if raise_error is True and user_id doesn't match
    """
    if not current_user.is_authenticated:
        if raise_error:
            abort(401, "Authentication required")
        return False

    matches = user_id == current_user.id

    if not matches:
        log_permission_error(current_user.id, "user_context", user_id, action="query")
        if raise_error:
            abort(403, "User context mismatch")

    return matches
