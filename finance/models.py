"""
Finance models for PinkLedger (Finflow).

Defines simple, small models for:
- Income
- Expense
- Budget

Each model is intentionally compact and focused on a single responsibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from finflow.app import db
from finflow.auth.model import User
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Income(db.Model):
    __tablename__ = "incomes"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount: Decimal = Column(Numeric(12, 2), nullable=False)
    source: str = Column(String(120), nullable=False)
    date: datetime = Column(DateTime, default=_utc_now, nullable=False)
    note: Optional[str] = Column(String(255), nullable=True)

    user = relationship("User", backref="incomes")

    __table_args__ = (CheckConstraint("amount >= 0", name="income_amount_nonnegative"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "source": self.source,
            "date": self.date.isoformat() if self.date else None,
            "note": self.note,
        }

    def __repr__(self) -> str:
        return f"<Income id={self.id} user_id={self.user_id} amount={self.amount}>"


class Expense(db.Model):
    __tablename__ = "expenses"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount: Decimal = Column(Numeric(12, 2), nullable=False)
    category: str = Column(String(50), nullable=False)
    date: datetime = Column(DateTime, default=_utc_now, nullable=False)
    note: Optional[str] = Column(String(255), nullable=True)

    user = relationship("User", backref="expenses")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="expense_amount_nonnegative"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "category": self.category,
            "date": self.date.isoformat() if self.date else None,
            "note": self.note,
        }

    def __repr__(self) -> str:
        return f"<Expense id={self.id} user_id={self.user_id} amount={self.amount} category={self.category}>"


class Budget(db.Model):
    __tablename__ = "budgets"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    month: str = Column(String(7), nullable=False, comment="Format: YYYY-MM")
    amount: Decimal = Column(Numeric(12, 2), nullable=False)

    user = relationship("User", backref="budgets")

    __table_args__ = (CheckConstraint("amount >= 0", name="budget_amount_nonnegative"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "month": self.month,
            "amount": float(self.amount) if self.amount is not None else 0.0,
        }

    def __repr__(self) -> str:
        return f"<Budget id={self.id} user_id={self.user_id} month={self.month} amount={self.amount}>"


class RecurringTransaction(db.Model):
    __tablename__ = "recurring_transactions"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    transaction_type: str = Column(String(10), nullable=False, comment="income or expense")
    amount: Decimal = Column(Numeric(12, 2), nullable=False)
    category_or_source: str = Column(String(120), nullable=False)
    frequency: str = Column(String(16), nullable=False, comment="daily, weekly, monthly")
    next_run_at: datetime = Column(DateTime, nullable=False)
    note: Optional[str] = Column(String(255), nullable=True)
    active: bool = Column(db.Boolean, default=True, nullable=False)
    created_at: datetime = Column(DateTime, default=_utc_now, nullable=False)

    user = relationship("User", backref="recurring_transactions")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="recurring_amount_nonnegative"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "category_or_source": self.category_or_source,
            "frequency": self.frequency,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "note": self.note,
            "active": bool(self.active),
        }


class SavingsGoal(db.Model):
    __tablename__ = "savings_goals"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: str = Column(String(120), nullable=False)
    target_amount: Decimal = Column(Numeric(12, 2), nullable=False)
    current_amount: Decimal = Column(Numeric(12, 2), nullable=False, default=0)
    deadline: Optional[datetime] = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, default=_utc_now, nullable=False)

    user = relationship("User", backref="savings_goals")

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="goal_target_positive"),
        CheckConstraint("current_amount >= 0", name="goal_current_nonnegative"),
    )

    def progress_percent(self) -> float:
        if not self.target_amount:
            return 0.0
        return min(100.0, float(self.current_amount / self.target_amount) * 100.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "target_amount": float(self.target_amount) if self.target_amount is not None else 0.0,
            "current_amount": float(self.current_amount) if self.current_amount is not None else 0.0,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "progress_percent": self.progress_percent(),
        }
