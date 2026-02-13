"""
Finance forms with validation for income, expense, and budget.

Forms:
- IncomeForm: Amount and source validation
- ExpenseForm: Amount and category validation
- BudgetForm: Category and limit validation
- DateRangeForm: Report date range selection

Uses Flask-WTF for CSRF protection and data validation.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    DecimalField,
    DateField,
    SelectField,
    TextAreaField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange


class IncomeForm(FlaskForm):
    """Form to add or edit income records."""

    amount = DecimalField(
        "Amount",
        validators=[
            DataRequired("Amount is required."),
            NumberRange(min=0.01, message="Amount must be greater than 0."),
        ],
        places=2,
    )
    source = StringField(
        "Source",
        validators=[
            DataRequired("Income source is required."),
            Length(min=2, max=120, message="Source must be 2-120 characters."),
        ],
    )
    date = DateField("Date", validators=[DataRequired("Date is required.")])
    note = TextAreaField("Note", validators=[Length(max=255)])
    submit = SubmitField("Save Income")


class ExpenseForm(FlaskForm):
    """Form to add or edit expense records."""

    CATEGORIES = [
        ("Food", "Food"),
        ("Travel", "Travel"),
        ("Shopping", "Shopping"),
        ("Bills", "Bills"),
        ("Others", "Others"),
    ]

    amount = DecimalField(
        "Amount",
        validators=[
            DataRequired("Amount is required."),
            NumberRange(min=0.01, message="Amount must be greater than 0."),
        ],
        places=2,
    )
    category = SelectField(
        "Category",
        choices=CATEGORIES,
        validators=[DataRequired("Category is required.")],
    )
    date = DateField("Date", validators=[DataRequired("Date is required.")])
    description = TextAreaField("Description", validators=[Length(max=255)])
    submit = SubmitField("Save Expense")


class BudgetForm(FlaskForm):
    """Form to add or edit budget records."""

    CATEGORIES = [
        ("Food", "Food"),
        ("Travel", "Travel"),
        ("Shopping", "Shopping"),
        ("Bills", "Bills"),
        ("Others", "Others"),
    ]

    category = SelectField(
        "Category",
        choices=CATEGORIES,
        validators=[DataRequired("Category is required.")],
    )
    limit = DecimalField(
        "Monthly Limit",
        validators=[
            DataRequired("Budget limit is required."),
            NumberRange(min=0.01, message="Limit must be greater than 0."),
        ],
        places=2,
    )
    submit = SubmitField("Set Budget")


class DateRangeForm(FlaskForm):
    """Form to filter reports by date range."""

    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])
    category = SelectField(
        "Category",
        choices=[
            ("all", "All Categories"),
            ("Food", "Food"),
            ("Travel", "Travel"),
            ("Shopping", "Shopping"),
            ("Bills", "Bills"),
            ("Others", "Others"),
        ],
    )
    submit = SubmitField("Generate Report")
