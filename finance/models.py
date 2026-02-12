"""
Finance models for PinkLedger (Finflow).

Defines simple, small models for:
- Income
- Expense
- Budget

Each model is intentionally compact and focused on a single responsibility.
"""

from __future__ import annotations

from datetime import datetime
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


class Income(db.Model):
    __tablename__ = "incomes"

    id: int = Column(Integer, primary_key=True)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount: Decimal = Column(Numeric(12, 2), nullable=False)
    source: str = Column(String(120), nullable=False)
    date: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
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
    date: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
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
