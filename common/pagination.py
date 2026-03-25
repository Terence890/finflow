"""
Pagination utilities for PinkLedger (Finflow).

Provides:
- Pagination helper class
- Query pagination
- Page calculation
"""

from typing import Any, Dict, List, Optional, TypeVar

from flask import request
from sqlalchemy.orm import Query

T = TypeVar("T")


class Paginator:
    """
    Helper class for pagination.

    Provides consistent pagination across list endpoints.
    """

    def __init__(
        self, query: Query, page: int = 1, per_page: int = 20, max_per_page: int = 100
    ):
        """
        Initialize paginator.

        Args:
            query: SQLAlchemy query object
            page: Current page (1-indexed)
            per_page: Items per page
            max_per_page: Maximum allowed per_page value
        """
        self.page = max(1, page)
        self.per_page = min(per_page, max_per_page)
        self.query = query

        # Get total count
        self.total = query.count()

        # Calculate pagination info
        self.total_pages = (self.total + self.per_page - 1) // self.per_page
        self.has_prev = self.page > 1
        self.has_next = self.page < self.total_pages
        self.prev_page = self.page - 1 if self.has_prev else None
        self.next_page = self.page + 1 if self.has_next else None

    def get_items(self) -> List[Any]:
        """
        Get items for current page.

        Returns:
            List of items for the current page
        """
        offset = (self.page - 1) * self.per_page
        return self.query.offset(offset).limit(self.per_page).all()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert pagination info to dictionary.

        Returns:
            Dictionary with pagination metadata
        """
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": self.total,
            "total_pages": self.total_pages,
            "has_prev": self.has_prev,
            "has_next": self.has_next,
            "prev_page": self.prev_page,
            "next_page": self.next_page,
        }


def get_page_from_request(default: int = 1) -> int:
    """
    Extract page number from request args.

    Args:
        default: Default page if not in request

    Returns:
        Page number (1-indexed)
    """
    try:
        page = int(request.args.get("page", default))
        return max(1, page)
    except (ValueError, TypeError):
        return default


def get_per_page_from_request(default: int = 20, max_per_page: int = 100) -> int:
    """
    Extract per_page from request args with safety checks.

    Args:
        default: Default per-page count
        max_per_page: Maximum allowed per-page

    Returns:
        Per-page value
    """
    try:
        per_page = int(request.args.get("per_page", default))
        return min(max(1, per_page), max_per_page)
    except (ValueError, TypeError):
        return default
