"""
Finance forms with validation for income, expense, and budget.

Forms:
- IncomeForm: Amount and source validation
- ExpenseForm: Amount and category validation
- BudgetForm: Category and limit validation
- DateRangeForm: Report date range selection
- FilterForm: List filtering and pagination

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
    IntegerField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional as OptionalValidator,
)


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

    month = StringField(
        "Month",
        validators=[
            DataRequired("Month is required."),
            Length(min=7, max=7, message="Month must be in YYYY-MM format."),
        ],
    )
    amount = DecimalField(
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


class TransactionFilterForm(FlaskForm):
    """Form to filter and paginate transactions."""
    
    page = IntegerField(
        "Page",
        validators=[OptionalValidator(), NumberRange(min=1, message="Page must be >= 1")],
        default=1,
    )
    per_page = IntegerField(
        "Per Page",
        validators=[OptionalValidator(), NumberRange(min=1, max=100)],
        default=20,
    )
    start_date = DateField("Start Date", validators=[OptionalValidator()])
    end_date = DateField("End Date", validators=[OptionalValidator()])
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
        default="all",
        validators=[OptionalValidator()],
    )
    min_amount = DecimalField(
        "Min Amount",
        validators=[OptionalValidator(), NumberRange(min=0)],
        places=2,
    )
    max_amount = DecimalField(
        "Max Amount",
        validators=[OptionalValidator(), NumberRange(min=0)],
        places=2,
    )
    q = StringField(
        "Search",
        validators=[OptionalValidator(), Length(max=120)],
    )
    
    def get_page(self) -> int:
        """Get page number with default."""
        return self.page.data if self.page.data else 1
    
    def get_per_page(self) -> int:
        """Get per_page value with default."""
        return min(self.per_page.data or 20, 100)


class IncomeFilterForm(TransactionFilterForm):
    """Form to filter incomes with source field."""
    
    source = StringField(
        "Source",
        validators=[OptionalValidator(), Length(max=120)],
    )


class ExpenseFilterForm(TransactionFilterForm):
    """Form to filter expenses (inherits from TransactionFilterForm)."""
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
        default="all",
        validators=[OptionalValidator()],
    )


class RecurringTransactionForm(FlaskForm):
    """Form to create recurring transactions."""

    transaction_type = SelectField(
        "Type",
        choices=[("income", "Income"), ("expense", "Expense")],
        validators=[DataRequired("Transaction type is required.")],
    )
    amount = DecimalField(
        "Amount",
        validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0.")],
        places=2,
    )
    category_or_source = StringField(
        "Category or Source",
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    frequency = SelectField(
        "Frequency",
        choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
        validators=[DataRequired("Frequency is required.")],
    )
    next_run_at = DateField("Next Run Date", validators=[DataRequired()])
    note = TextAreaField("Note", validators=[OptionalValidator(), Length(max=255)])
    submit = SubmitField("Add Recurring")


class SavingsGoalForm(FlaskForm):
    """Form to create or update savings goals."""

    name = StringField("Goal Name", validators=[DataRequired(), Length(min=2, max=120)])
    target_amount = DecimalField(
        "Target Amount",
        validators=[DataRequired(), NumberRange(min=1, message="Target must be at least 1.")],
        places=2,
    )
    current_amount = DecimalField(
        "Current Amount",
        validators=[OptionalValidator(), NumberRange(min=0)],
        places=2,
        default=0,
    )
    deadline = DateField("Deadline", validators=[OptionalValidator()])
    submit = SubmitField("Save Goal")

