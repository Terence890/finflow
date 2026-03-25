from __future__ import annotations

from datetime import datetime, timezone

from finflow.app import db
from finflow.common.logger import finance_logger, log_transaction
from finflow.common.pagination import (
    Paginator,
    get_page_from_request,
    get_per_page_from_request,
)
from finflow.common.permissions import require_owned_by_user, validate_user_context
from finflow.finance.forms import (
    BudgetForm,
    DateRangeForm,
    ExpenseFilterForm,
    ExpenseForm,
    IncomeFilterForm,
    IncomeForm,
)
from finflow.finance.models import Budget, Expense, Income
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

finance_bp = Blueprint(
    "finance", __name__, template_folder="../templates", static_folder="../static"
)


@finance_bp.route("/dashboard")
@login_required
def dashboard():
    """Render dashboard and keep all queries constrained to current user."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    total_income = (
        db.session.query(db.func.coalesce(db.func.sum(Income.amount), 0))
        .filter(Income.user_id == uid)
        .scalar()
        or 0
    )
    total_expense = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.user_id == uid)
        .scalar()
        or 0
    )
    balance = float(total_income) - float(total_expense)

    incomes = (
        Income.query.filter_by(user_id=uid).order_by(Income.date.desc()).limit(5).all()
    )
    expenses = (
        Expense.query.filter_by(user_id=uid)
        .order_by(Expense.date.desc())
        .limit(5)
        .all()
    )

    category_rows = (
        db.session.query(
            Expense.category, db.func.coalesce(db.func.sum(Expense.amount), 0)
        )
        .filter(Expense.user_id == uid)
        .group_by(Expense.category)
        .all()
    )
    categories = [
        {"category": c or "Others", "amount": float(a)} for c, a in category_rows
    ]

    finance_logger.info("User %s accessed dashboard", uid)
    return render_template(
        "dashboard.html",
        total_income=float(total_income),
        total_expense=float(total_expense),
        balance=float(balance),
        incomes=incomes,
        expenses=expenses,
        expense_by_category=categories,
        today=datetime.now(timezone.utc).date().isoformat(),
    )


@finance_bp.route("/income", methods=["POST"])
@login_required
def add_income():
    """Create income via Flask-WTF form validation."""
    uid = current_user.id
    form = IncomeForm()

    if not form.validate_on_submit():
        flash("Invalid income data. Please review the form fields.", "danger")
        finance_logger.warning("Invalid income form submission by user %s", uid)
        return redirect(url_for("finance.income_page"))

    try:
        income = Income(
            user_id=uid,
            amount=form.amount.data,
            source=form.source.data.strip(),
            date=form.date.data,
            note=form.note.data.strip() if form.note.data else None,
        )
        db.session.add(income)
        db.session.commit()
        log_transaction(
            uid, "income", income.source, float(income.amount), status="success"
        )
        flash("Income added successfully.", "success")
        return redirect(url_for("finance.income_page"))
    except Exception as exc:
        db.session.rollback()
        log_transaction(
            uid,
            "income",
            form.source.data or "Income",
            float(form.amount.data or 0),
            status="failed",
            details=str(exc),
        )
        finance_logger.error("Failed to create income for user %s: %s", uid, exc)
        flash("Unable to add income right now.", "danger")
        return redirect(url_for("finance.income_page"))


@finance_bp.route("/income", methods=["GET"])
@login_required
def list_incomes():
    """JSON list endpoint with filters and pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    filter_form = IncomeFilterForm(formdata=request.args, meta={"csrf": False})
    page = get_page_from_request()
    per_page = get_per_page_from_request()

    query = Income.query.filter_by(user_id=uid)
    if filter_form.validate():
        if filter_form.start_date.data:
            query = query.filter(Income.date >= filter_form.start_date.data)
        if filter_form.end_date.data:
            query = query.filter(Income.date <= filter_form.end_date.data)
        if filter_form.min_amount.data is not None:
            query = query.filter(Income.amount >= filter_form.min_amount.data)
        if filter_form.max_amount.data is not None:
            query = query.filter(Income.amount <= filter_form.max_amount.data)
        if filter_form.source.data:
            query = query.filter(
                Income.source.ilike(f"%{filter_form.source.data.strip()}%")
            )

    query = query.order_by(Income.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()

    return jsonify(
        {"incomes": [i.to_dict() for i in items], "pagination": paginator.to_dict()}
    )


@finance_bp.route("/income/list", methods=["GET"])
@login_required
def income_page():
    """HTML page for incomes with filters and pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    filter_form = IncomeFilterForm(formdata=request.args, meta={"csrf": False})
    page = get_page_from_request()
    per_page = get_per_page_from_request()

    query = Income.query.filter_by(user_id=uid)
    if filter_form.validate():
        if filter_form.start_date.data:
            query = query.filter(Income.date >= filter_form.start_date.data)
        if filter_form.end_date.data:
            query = query.filter(Income.date <= filter_form.end_date.data)
        if filter_form.min_amount.data is not None:
            query = query.filter(Income.amount >= filter_form.min_amount.data)
        if filter_form.max_amount.data is not None:
            query = query.filter(Income.amount <= filter_form.max_amount.data)
        if filter_form.source.data:
            query = query.filter(
                Income.source.ilike(f"%{filter_form.source.data.strip()}%")
            )

    query = query.order_by(Income.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)

    finance_logger.info(
        "User %s viewed income list page=%s per_page=%s", uid, page, per_page
    )
    return render_template(
        "income.html",
        incomes=paginator.get_items(),
        paginator=paginator,
        filter_form=filter_form,
        form=IncomeForm(),
        today=datetime.now(timezone.utc).date().isoformat(),
    )


@finance_bp.route("/income/<int:item_id>", methods=["DELETE"])
@login_required
@require_owned_by_user(Income, id_param="item_id")
def delete_income(item_id: int):
    """Delete an income row owned by the current user."""
    uid = current_user.id
    income = Income.query.get_or_404(item_id)
    try:
        amount = float(income.amount)
        source = income.source or "Income"
        db.session.delete(income)
        db.session.commit()
        log_transaction(uid, "income_delete", source, amount, status="success")
        return jsonify({"deleted": True}), 200
    except Exception as exc:
        db.session.rollback()
        finance_logger.error(
            "Failed deleting income %s for user %s: %s", item_id, uid, exc
        )
        return jsonify({"error": "Failed to delete income"}), 500


@finance_bp.route("/expense", methods=["POST"])
@login_required
def add_expense():
    """Create expense via Flask-WTF form validation."""
    uid = current_user.id
    form = ExpenseForm()

    if not form.validate_on_submit():
        flash("Invalid expense data. Please review the form fields.", "danger")
        finance_logger.warning("Invalid expense form submission by user %s", uid)
        return redirect(url_for("finance.expense_page"))

    try:
        expense = Expense(
            user_id=uid,
            amount=form.amount.data,
            category=form.category.data,
            date=form.date.data,
            note=form.description.data.strip() if form.description.data else None,
        )
        db.session.add(expense)
        db.session.commit()
        log_transaction(
            uid, "expense", expense.category, float(expense.amount), status="success"
        )
        flash("Expense added successfully.", "success")
        return redirect(url_for("finance.expense_page"))
    except Exception as exc:
        db.session.rollback()
        log_transaction(
            uid,
            "expense",
            form.category.data or "Others",
            float(form.amount.data or 0),
            status="failed",
            details=str(exc),
        )
        finance_logger.error("Failed to create expense for user %s: %s", uid, exc)
        flash("Unable to add expense right now.", "danger")
        return redirect(url_for("finance.expense_page"))


@finance_bp.route("/expense", methods=["GET"])
@login_required
def list_expenses():
    """JSON list endpoint with filters and pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    filter_form = ExpenseFilterForm(formdata=request.args, meta={"csrf": False})
    page = get_page_from_request()
    per_page = get_per_page_from_request()

    query = Expense.query.filter_by(user_id=uid)
    if filter_form.validate():
        if filter_form.start_date.data:
            query = query.filter(Expense.date >= filter_form.start_date.data)
        if filter_form.end_date.data:
            query = query.filter(Expense.date <= filter_form.end_date.data)
        if filter_form.min_amount.data is not None:
            query = query.filter(Expense.amount >= filter_form.min_amount.data)
        if filter_form.max_amount.data is not None:
            query = query.filter(Expense.amount <= filter_form.max_amount.data)
        if filter_form.category.data and filter_form.category.data != "all":
            query = query.filter(Expense.category == filter_form.category.data)

    query = query.order_by(Expense.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()

    return jsonify(
        {"expenses": [e.to_dict() for e in items], "pagination": paginator.to_dict()}
    )


@finance_bp.route("/expense/list", methods=["GET"])
@login_required
def expense_page():
    """HTML page for expenses with filters and pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    filter_form = ExpenseFilterForm(formdata=request.args, meta={"csrf": False})
    page = get_page_from_request()
    per_page = get_per_page_from_request()

    query = Expense.query.filter_by(user_id=uid)
    if filter_form.validate():
        if filter_form.start_date.data:
            query = query.filter(Expense.date >= filter_form.start_date.data)
        if filter_form.end_date.data:
            query = query.filter(Expense.date <= filter_form.end_date.data)
        if filter_form.min_amount.data is not None:
            query = query.filter(Expense.amount >= filter_form.min_amount.data)
        if filter_form.max_amount.data is not None:
            query = query.filter(Expense.amount <= filter_form.max_amount.data)
        if filter_form.category.data and filter_form.category.data != "all":
            query = query.filter(Expense.category == filter_form.category.data)

    query = query.order_by(Expense.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)

    finance_logger.info(
        "User %s viewed expense list page=%s per_page=%s", uid, page, per_page
    )
    return render_template(
        "expense.html",
        expenses=paginator.get_items(),
        paginator=paginator,
        filter_form=filter_form,
        form=ExpenseForm(),
        today=datetime.now(timezone.utc).date().isoformat(),
    )


@finance_bp.route("/expense/<int:item_id>", methods=["DELETE"])
@login_required
@require_owned_by_user(Expense, id_param="item_id")
def delete_expense(item_id: int):
    """Delete an expense row owned by the current user."""
    uid = current_user.id
    expense = Expense.query.get_or_404(item_id)
    try:
        amount = float(expense.amount)
        category = expense.category or "Others"
        db.session.delete(expense)
        db.session.commit()
        log_transaction(uid, "expense_delete", category, amount, status="success")
        return jsonify({"deleted": True}), 200
    except Exception as exc:
        db.session.rollback()
        finance_logger.error(
            "Failed deleting expense %s for user %s: %s", item_id, uid, exc
        )
        return jsonify({"error": "Failed to delete expense"}), 500


@finance_bp.route("/budget", methods=["GET"])
@login_required
def budget_page():
    """Show budget page for selected month."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    current_month = request.args.get("month") or datetime.now(timezone.utc).strftime(
        "%Y-%m"
    )
    budget = Budget.query.filter_by(user_id=uid, month=current_month).first()
    form = BudgetForm(month=current_month)

    finance_logger.info("User %s viewed budget month=%s", uid, current_month)
    return render_template(
        "budget.html", budget=budget, current_month=current_month, form=form
    )


@finance_bp.route("/budget", methods=["POST"])
@login_required
def set_budget():
    """Create/update monthly budget via WTForms."""
    uid = current_user.id
    form = BudgetForm()

    if not form.validate_on_submit():
        flash(
            "Invalid budget data. Use month format YYYY-MM and a valid amount.",
            "danger",
        )
        return redirect(
            url_for("finance.budget_page", month=request.form.get("month", ""))
        )

    month = form.month.data.strip()
    amount = form.amount.data

    try:
        budget = Budget.query.filter_by(user_id=uid, month=month).first()
        if budget is None:
            budget = Budget(user_id=uid, month=month, amount=amount)
            db.session.add(budget)
        else:
            budget.amount = amount
        db.session.commit()

        log_transaction(
            uid,
            "budget",
            "monthly",
            float(amount),
            status="success",
            details=f"month={month}",
        )
        flash("Budget saved successfully.", "success")
        return redirect(url_for("finance.budget_page", month=month))
    except Exception as exc:
        db.session.rollback()
        finance_logger.error(
            "Failed saving budget for user %s month=%s: %s", uid, month, exc
        )
        flash("Unable to save budget right now.", "danger")
        return redirect(url_for("finance.budget_page", month=month))


@finance_bp.route("/api/summary")
@login_required
def api_summary():
    """Return summary payload for charts/widgets."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    total_income = (
        db.session.query(db.func.coalesce(db.func.sum(Income.amount), 0))
        .filter(Income.user_id == uid)
        .scalar()
        or 0
    )
    total_expense = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.user_id == uid)
        .scalar()
        or 0
    )

    return jsonify(
        {
            "income": float(total_income),
            "expense": float(total_expense),
            "balance": float(total_income) - float(total_expense),
        }
    )


@finance_bp.route("/reports", methods=["GET"])
@login_required
def reports_page():
    """Render reports with optional date/category filter."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    form = DateRangeForm(formdata=request.args, meta={"csrf": False})

    income_query = Income.query.filter_by(user_id=uid)
    expense_query = Expense.query.filter_by(user_id=uid)

    if form.validate() and form.start_date.data and form.end_date.data:
        income_query = income_query.filter(
            Income.date >= form.start_date.data, Income.date <= form.end_date.data
        )
        expense_query = expense_query.filter(
            Expense.date >= form.start_date.data, Expense.date <= form.end_date.data
        )
        if form.category.data and form.category.data != "all":
            expense_query = expense_query.filter(Expense.category == form.category.data)

    total_income = (
        db.session.query(
            db.func.coalesce(db.func.sum(income_query.subquery().c.amount), 0)
        ).scalar()
        or 0
    )
    total_expense = (
        db.session.query(
            db.func.coalesce(db.func.sum(expense_query.subquery().c.amount), 0)
        ).scalar()
        or 0
    )

    category_rows = (
        expense_query.with_entities(
            Expense.category, db.func.coalesce(db.func.sum(Expense.amount), 0)
        )
        .group_by(Expense.category)
        .all()
    )
    categories = [
        {"category": c or "Other", "amount": float(a)} for c, a in category_rows
    ]

    summary = {
        "income": float(total_income),
        "expense": float(total_expense),
        "balance": float(total_income) - float(total_expense),
    }

    finance_logger.info("User %s viewed reports", uid)
    return render_template(
        "reports.html", summary=summary, categories=categories, form=form
    )
