"""
Logging configuration for PinkLedger (Finflow).

Provides:
- Centralized logging setup
- Request/response logging
- Financial transaction logging
- Error/warning logging
"""

import logging
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Create console handler with formatting
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


# Module-level loggers
auth_logger = get_logger("finflow.auth")
finance_logger = get_logger("finflow.finance")
service_logger = get_logger("finflow.service")
db_logger = get_logger("finflow.database")


def log_transaction(
    user_id: int,
    transaction_type: str,
    category: str,
    amount: float,
    status: str = "success",
    details: Optional[str] = None
) -> None:
    """
    Log a financial transaction.
    
    Args:
        user_id: User ID
        transaction_type: "income" or "expense"
        category: Transaction category
        amount: Transaction amount
        status: "success" or "failed"
        details: Additional details
    """
    message = (
        f"User {user_id} | {transaction_type.upper()} | "
        f"Category: {category} | Amount: {amount} | Status: {status}"
    )
    if details:
        message += f" | Details: {details}"
    
    if status == "success":
        finance_logger.info(message)
    else:
        finance_logger.warning(message)


def log_auth_event(
    event: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    status: str = "success"
) -> None:
    """
    Log authentication events.
    
    Args:
        event: "login", "logout", "register", etc.
        user_id: User ID (optional)
        email: User email (optional)
        status: "success" or "failed"
    """
    identifier = email or f"user_{user_id}" if user_id else "unknown"
    message = f"{event.upper()} | {identifier} | Status: {status}"
    
    if status == "success":
        auth_logger.info(message)
    else:
        auth_logger.warning(message)


def log_permission_error(
    user_id: int,
    resource_type: str,
    resource_id: int,
    action: str = "access"
) -> None:
    """
    Log permission/authorization errors.
    
    Args:
        user_id: Attempting user ID
        resource_type: Type of resource (income, expense, budget)
        resource_id: Resource ID
        action: Action attempted (access, delete, modify)
    """
    service_logger.warning(
        f"Permission denied | User {user_id} attempted to {action} "
        f"{resource_type} {resource_id}"
    )
