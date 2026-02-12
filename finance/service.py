"""
Finance service layer for PinkLedger (Finflow).

Purpose:
- Encapsulate business logic for incomes, expenses and budgets.
- Keep route handlers small and focused on HTTP concerns.
- Provide clear, typed APIs that return (result, error) tuples where useful.

Notes:
- Uses SQLAlchemy models defined in `Finflow.finance.models`.
- Uses the shared `db` instance from `Finflow.app`.
"""

from __future__ import annotations

from datetime import date, datetime
from io import StringIO
from typing import Dict, List, Optional, Tuple

from finflow.app import db
from finflow.finance.models import Budget, Expense, Income


def add_income(
    user_id: int,
    amount: float,
    source: Optional[str] = None,
    when: Optional[date] = None,
) -> Tuple[Optional[Income], Optional[str]]:
    """Create and persist an Income. Returns (income, error)."""
    if amount is None:
        return None, "Amount is required."
    try:
        amt = float(amount)
        if amt < 0:
            return None, "Amount must be non-negative."
    except Exception:
        return None, "Invalid amount."

    when = when or datetime.utcnow().date()
    src = (source or "Income").strip()

    income = Income(user_id=user_id, amount=amt, source=src, date=when)
    try:
        db.session.add(income)
        db.session.commit()
        return income, None
    except Exception as exc:  # pragma: no cover - bubble DB issues
        db.session.rollback()
        return None, f"Database error: {exc}"


def add_expense(
    user_id: int,
    amount: float,
    category: str,
    when: Optional[date] = None,
) -> Tuple[Optional[Expense], Optional[str]]:
    """Create and persist an Expense. Returns (expense, error)."""
    if amount is None:
        return None, "Amount is required."
    try:
        amt = float(amount)
        if amt < 0:
            return None, "Amount must be non-negative."
    except Exception:
        return None, "Invalid amount."

    if not category:
        return None, "Category is required."

    when = when or datetime.utcnow().date()
    cat = category.strip()

    expense = Expense(user_id=user_id, amount=amt, category=cat, date=when)
    try:
        db.session.add(expense)
        db.session.commit()
        return expense, None
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        return None, f"Database error: {exc}"


def get_totals(user_id: int) -> Dict[str, float]:
    """Return aggregated totals: income, expense and balance for the user."""
    total_income = (
        db.session.query(db.func.coalesce(db.func.sum(Income.amount), 0))
        .filter(Income.user_id == user_id)
        .scalar()
    ) or 0.0
    total_expense = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.user_id == user_id)
        .scalar()
    ) or 0.0
    return {
        "income": float(total_income),
        "expense": float(total_expense),
        "balance": float(total_income) - float(total_expense),
    }


def get_recent_incomes(user_id: int, limit: int = 5) -> List[Income]:
    """Return recent incomes ordered by date desc."""
    return (
        Income.query.filter_by(user_id=user_id)
        .order_by(Income.date.desc())
        .limit(limit)
        .all()
    )


def get_recent_expenses(user_id: int, limit: int = 5) -> List[Expense]:
    """Return recent expenses ordered by date desc."""
    return (
        Expense.query.filter_by(user_id=user_id)
        .order_by(Expense.date.desc())
        .limit(limit)
        .all()
    )


def expense_by_category(user_id: int) -> List[Dict[str, float]]:
    """Return list of {category, amount} for the user's expenses."""
    rows = (
        db.session.query(
            Expense.category, db.func.coalesce(db.func.sum(Expense.amount), 0)
        )
        .filter(Expense.user_id == user_id)
        .group_by(Expense.category)
        .all()
    )
    return [{"category": r[0] or "Uncategorized", "amount": float(r[1])} for r in rows]


def set_budget(
    user_id: int, month: str, amount: float
) -> Tuple[Optional[Budget], Optional[str]]:
    """
    Create or update a monthly budget for the user.
    `month` expected in 'YYYY-MM' format.
    """
    if not month:
        return None, "Month is required."
    try:
        amt = float(amount)
        if amt < 0:
            return None, "Amount must be non-negative."
    except Exception:
        return None, "Invalid amount."

    try:
        b = Budget.query.filter_by(user_id=user_id, month=month).first()
        if not b:
            b = Budget(user_id=user_id, month=month, amount=amt)
            db.session.add(b)
        else:
            b.amount = amt
        db.session.commit()
        return b, None
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        return None, f"Database error: {exc}"


def get_budget(user_id: int, month: str) -> Optional[Budget]:
    """Return Budget for the given user and month, or None."""
    if not month:
        return None
    return Budget.query.filter_by(user_id=user_id, month=month).first()


def export_transactions_csv(user_id: int) -> str:
    """
    Export incomes and expenses as CSV string.
    Columns: type,date,amount,category/source,note
    """
    out = StringIO()
    out.write("type,date,amount,category_or_source,note\n")

    incomes = Income.query.filter_by(user_id=user_id).order_by(Income.date.asc()).all()
    expenses = (
        Expense.query.filter_by(user_id=user_id).order_by(Expense.date.asc()).all()
    )

    # Merge by date for a simple chronological export
    items = []
    for i in incomes:
        items.append(
            (
                "income",
                i.date.isoformat() if i.date else "",
                float(i.amount),
                i.source or "",
                getattr(i, "note", "") or "",
            )
        )
    for e in expenses:
        items.append(
            (
                "expense",
                e.date.isoformat() if e.date else "",
                float(e.amount),
                e.category or "",
                getattr(e, "note", "") or "",
            )
        )
    # sort by date then type
    items.sort(key=lambda t: (t[1] or "", t[0]))

    for ttype, dt, amt, tag, note in items:
        out.write(f'{ttype},{dt},{amt:.2f},"{tag}","{note}"\n')

    return out.getvalue()
