"""Initial database schema for PinkLedger.

This migration creates the initial tables:
- users: User accounts with authentication
- incomes: Income tracking
- expenses: Expense tracking
- budgets: Budget planning

Revision ID: 001_initial_schema
Create Date: 2024-01-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from datetime import datetime

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial database tables."""
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(120), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="unique_user_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Incomes table
    op.create_table(
        "incomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount >= 0", name="income_amount_nonnegative"),
    )
    op.create_index("ix_incomes_user_id", "incomes", ["user_id"])

    # Expenses table
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount >= 0", name="expense_amount_nonnegative"),
    )
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"])

    # Budgets table
    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("limit", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("limit > 0", name="budget_limit_positive"),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])


def downgrade():
    """Drop all tables."""
    op.drop_index("ix_budgets_user_id", table_name="budgets")
    op.drop_table("budgets")
    op.drop_index("ix_expenses_user_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_incomes_user_id", table_name="incomes")
    op.drop_table("incomes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
