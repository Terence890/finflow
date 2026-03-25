from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Tuple

from finflow.app import db
from finflow.common.logger import finance_logger, log_transaction
from finflow.common.pagination import Paginator, get_page_from_request, get_per_page_from_request
from finflow.common.permissions import require_owned_by_user, validate_user_context
from finflow.finance.forms import (
    BudgetForm,
    DateRangeForm,
    ExpenseFilterForm,
    ExpenseForm,
    IncomeFilterForm,
    IncomeForm,
    RecurringTransactionForm,
    SavingsGoalForm,
)
from finflow.finance.models import (
    Budget,
    Expense,
    Income,
    RecurringTransaction,
    SavingsGoal,
)
from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

finance_bp = Blueprint(
    "finance", __name__, template_folder="../templates", static_folder="../static"
)


def _month_bounds(month: str) -> Tuple[date, date]:
    year, month_num = map(int, month.split("-"))
    start = date(year, month_num, 1)
    if month_num == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month_num + 1, 1)
    return start, end


def _budget_alert_for_month(user_id: int, month: str) -> Dict[str, Any]:
    budget = Budget.query.filter_by(user_id=user_id, month=month).first()
    if not budget:
        return {"has_budget": False, "percent": 0.0, "level": "none", "message": "No budget set for this month."}

    start, end = _month_bounds(month)
    spent = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.user_id == user_id, Expense.date >= start, Expense.date < end)
        .scalar()
        or 0
    )

    budget_amount = float(budget.amount or 0)
    spent_amount = float(spent or 0)
    percent = (spent_amount / budget_amount * 100.0) if budget_amount > 0 else 0.0

    if percent >= 100:
        level = "danger"
        message = "Budget exceeded (100%+)."
    elif percent >= 80:
        level = "warning"
        message = "Budget is above 80%."
    elif percent >= 50:
        level = "info"
        message = "Budget has reached 50%."
    else:
        level = "safe"
        message = "Budget is healthy."

    return {
        "has_budget": True,
        "budget": budget_amount,
        "spent": spent_amount,
        "percent": round(percent, 2),
        "level": level,
        "message": message,
        "month": month,
    }


def _next_run(current: datetime, frequency: str) -> datetime:
    if frequency == "daily":
        return current + timedelta(days=1)
    if frequency == "weekly":
        return current + timedelta(weeks=1)
    return current + timedelta(days=30)


def _simple_pdf_bytes(title: str, lines: List[str]) -> bytes:
    """Very small PDF generator for text reports (no external deps)."""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    y = 800
    parts = ["BT /F1 12 Tf 50 820 Td ({}) Tj ET".format(esc(title))]
    for line in lines:
        y -= 16
        parts.append(f"BT /F1 10 Tf 50 {y} Td ({esc(line)}) Tj ET")

    content = "\n".join(parts).encode("latin-1", "ignore")
    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n")
    objects.append((f"4 0 obj << /Length {len(content)} >> stream\n").encode() + content + b"\nendstream endobj\n")
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())
    return bytes(pdf)


@finance_bp.route("/dashboard")
@login_required
def dashboard():
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

    incomes = Income.query.filter_by(user_id=uid).order_by(Income.date.desc()).limit(5).all()
    expenses = Expense.query.filter_by(user_id=uid).order_by(Expense.date.desc()).limit(5).all()

    category_rows = (
        db.session.query(Expense.category, db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.user_id == uid)
        .group_by(Expense.category)
        .all()
    )
    categories = [{"category": c or "Others", "amount": float(a)} for c, a in category_rows]

    now_month = datetime.now(UTC).strftime("%Y-%m")
    budget_alert = _budget_alert_for_month(uid, now_month)
    goals = SavingsGoal.query.filter_by(user_id=uid).order_by(SavingsGoal.created_at.desc()).limit(4).all()
    recurring = (
        RecurringTransaction.query.filter_by(user_id=uid, active=True)
        .order_by(RecurringTransaction.next_run_at.asc())
        .limit(5)
        .all()
    )

    finance_logger.info("User %s accessed dashboard", uid)
    return render_template(
        "dashboard.html",
        total_income=float(total_income),
        total_expense=float(total_expense),
        balance=float(balance),
        incomes=incomes,
        expenses=expenses,
        expense_by_category=categories,
        budget_alert=budget_alert,
        savings_goals=goals,
        recurring_items=recurring,
        recurring_form=RecurringTransactionForm(),
        goal_form=SavingsGoalForm(),
        today=datetime.now(UTC).date().isoformat(),
    )


@finance_bp.route("/income", methods=["POST"])
@login_required
def add_income():
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
        log_transaction(uid, "income", income.source, float(income.amount), status="success")
        flash("Income added successfully.", "success")
        return redirect(url_for("finance.income_page"))
    except Exception as exc:
        db.session.rollback()
        log_transaction(uid, "income", form.source.data or "Income", float(form.amount.data or 0), status="failed", details=str(exc))
        finance_logger.error("Failed to create income for user %s: %s", uid, exc)
        flash("Unable to add income right now.", "danger")
        return redirect(url_for("finance.income_page"))


@finance_bp.route("/income", methods=["GET"])
@login_required
def list_incomes():
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
            query = query.filter(Income.source.ilike(f"%{filter_form.source.data.strip()}%"))
        if filter_form.q.data:
            term = f"%{filter_form.q.data.strip()}%"
            query = query.filter(db.or_(Income.source.ilike(term), Income.note.ilike(term)))

    query = query.order_by(Income.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()

    return jsonify({"incomes": [i.to_dict() for i in items], "pagination": paginator.to_dict()})


@finance_bp.route("/income/list", methods=["GET"])
@login_required
def income_page():
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
            query = query.filter(Income.source.ilike(f"%{filter_form.source.data.strip()}%"))
        if filter_form.q.data:
            term = f"%{filter_form.q.data.strip()}%"
            query = query.filter(db.or_(Income.source.ilike(term), Income.note.ilike(term)))

    query = query.order_by(Income.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)

    return render_template(
        "income.html",
        incomes=paginator.get_items(),
        paginator=paginator,
        filter_form=filter_form,
        form=IncomeForm(),
        today=datetime.now(UTC).date().isoformat(),
    )


@finance_bp.route("/income/<int:item_id>", methods=["DELETE"])
@login_required
@require_owned_by_user(Income, id_param="item_id")
def delete_income(item_id: int):
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
        finance_logger.error("Failed deleting income %s for user %s: %s", item_id, uid, exc)
        return jsonify({"error": "Failed to delete income"}), 500


@finance_bp.route("/expense", methods=["POST"])
@login_required
def add_expense():
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
        log_transaction(uid, "expense", expense.category, float(expense.amount), status="success")
        flash("Expense added successfully.", "success")
        return redirect(url_for("finance.expense_page"))
    except Exception as exc:
        db.session.rollback()
        log_transaction(uid, "expense", form.category.data or "Others", float(form.amount.data or 0), status="failed", details=str(exc))
        finance_logger.error("Failed to create expense for user %s: %s", uid, exc)
        flash("Unable to add expense right now.", "danger")
        return redirect(url_for("finance.expense_page"))


@finance_bp.route("/expense", methods=["GET"])
@login_required
def list_expenses():
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
        if filter_form.q.data:
            term = f"%{filter_form.q.data.strip()}%"
            query = query.filter(db.or_(Expense.category.ilike(term), Expense.note.ilike(term)))

    query = query.order_by(Expense.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()

    return jsonify({"expenses": [e.to_dict() for e in items], "pagination": paginator.to_dict()})


@finance_bp.route("/expense/list", methods=["GET"])
@login_required
def expense_page():
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
        if filter_form.q.data:
            term = f"%{filter_form.q.data.strip()}%"
            query = query.filter(db.or_(Expense.category.ilike(term), Expense.note.ilike(term)))

    query = query.order_by(Expense.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)

    return render_template(
        "expense.html",
        expenses=paginator.get_items(),
        paginator=paginator,
        filter_form=filter_form,
        form=ExpenseForm(),
        today=datetime.now(UTC).date().isoformat(),
    )


@finance_bp.route("/expense/<int:item_id>", methods=["DELETE"])
@login_required
@require_owned_by_user(Expense, id_param="item_id")
def delete_expense(item_id: int):
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
        finance_logger.error("Failed deleting expense %s for user %s: %s", item_id, uid, exc)
        return jsonify({"error": "Failed to delete expense"}), 500


@finance_bp.route("/budget", methods=["GET"])
@login_required
def budget_page():
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    current_month = request.args.get("month") or datetime.now(UTC).strftime("%Y-%m")
    budget = Budget.query.filter_by(user_id=uid, month=current_month).first()
    form = BudgetForm(month=current_month)
    goal_form = SavingsGoalForm()
    goals = SavingsGoal.query.filter_by(user_id=uid).order_by(SavingsGoal.created_at.desc()).all()
    budget_alert = _budget_alert_for_month(uid, current_month)

    return render_template(
        "budget.html",
        budget=budget,
        current_month=current_month,
        form=form,
        goal_form=goal_form,
        goals=goals,
        budget_alert=budget_alert,
    )


@finance_bp.route("/budget", methods=["POST"])
@login_required
def set_budget():
    uid = current_user.id
    form = BudgetForm()

    if not form.validate_on_submit():
        flash("Invalid budget data. Use month format YYYY-MM and a valid amount.", "danger")
        return redirect(url_for("finance.budget_page", month=request.form.get("month", "")))

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

        log_transaction(uid, "budget", "monthly", float(amount), status="success", details=f"month={month}")
        flash("Budget saved successfully.", "success")
        return redirect(url_for("finance.budget_page", month=month))
    except Exception as exc:
        db.session.rollback()
        finance_logger.error("Failed saving budget for user %s month=%s: %s", uid, month, exc)
        flash("Unable to save budget right now.", "danger")
        return redirect(url_for("finance.budget_page", month=month))


@finance_bp.route("/goals", methods=["POST"])
@login_required
def save_goal():
    uid = current_user.id
    form = SavingsGoalForm()

    if not form.validate_on_submit():
        flash("Invalid savings goal data.", "danger")
        return redirect(url_for("finance.budget_page"))

    goal = SavingsGoal(
        user_id=uid,
        name=form.name.data.strip(),
        target_amount=form.target_amount.data,
        current_amount=form.current_amount.data or 0,
        deadline=form.deadline.data,
    )
    db.session.add(goal)
    db.session.commit()
    flash("Savings goal saved.", "success")
    return redirect(url_for("finance.budget_page"))


@finance_bp.route("/recurring", methods=["POST"])
@login_required
def add_recurring():
    uid = current_user.id
    form = RecurringTransactionForm()

    if not form.validate_on_submit():
        flash("Invalid recurring transaction data.", "danger")
        return redirect(url_for("finance.dashboard"))

    next_run = datetime.combine(form.next_run_at.data, datetime.min.time(), tzinfo=UTC)
    item = RecurringTransaction(
        user_id=uid,
        transaction_type=form.transaction_type.data,
        amount=form.amount.data,
        category_or_source=form.category_or_source.data.strip(),
        frequency=form.frequency.data,
        next_run_at=next_run,
        note=form.note.data.strip() if form.note.data else None,
        active=True,
    )
    db.session.add(item)
    db.session.commit()
    flash("Recurring transaction created.", "success")
    return redirect(url_for("finance.dashboard"))


@finance_bp.route("/recurring/<int:item_id>/run", methods=["POST"])
@login_required
@require_owned_by_user(RecurringTransaction, id_param="item_id")
def run_recurring(item_id: int):
    uid = current_user.id
    item = RecurringTransaction.query.get_or_404(item_id)

    if not item.active:
        return jsonify({"error": "Recurring transaction is inactive."}), 400

    if item.transaction_type == "income":
        tx = Income(
            user_id=uid,
            amount=item.amount,
            source=item.category_or_source,
            date=datetime.now(UTC).date(),
            note=item.note,
        )
        db.session.add(tx)
        log_transaction(uid, "income", item.category_or_source, float(item.amount), status="success", details="recurring run")
    else:
        tx = Expense(
            user_id=uid,
            amount=item.amount,
            category=item.category_or_source,
            date=datetime.now(UTC).date(),
            note=item.note,
        )
        db.session.add(tx)
        log_transaction(uid, "expense", item.category_or_source, float(item.amount), status="success", details="recurring run")

    item.next_run_at = _next_run(item.next_run_at, item.frequency)
    db.session.commit()
    return jsonify({"ok": True, "next_run_at": item.next_run_at.isoformat()})


@finance_bp.route("/api/summary")
@login_required
def api_summary():
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
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    form = DateRangeForm(formdata=request.args, meta={"csrf": False})
    q = (request.args.get("q") or "").strip()

    income_query = Income.query.filter_by(user_id=uid)
    expense_query = Expense.query.filter_by(user_id=uid)

    if form.validate() and form.start_date.data and form.end_date.data:
        income_query = income_query.filter(Income.date >= form.start_date.data, Income.date <= form.end_date.data)
        expense_query = expense_query.filter(Expense.date >= form.start_date.data, Expense.date <= form.end_date.data)
        if form.category.data and form.category.data != "all":
            expense_query = expense_query.filter(Expense.category == form.category.data)

    if q:
        term = f"%{q}%"
        income_query = income_query.filter(db.or_(Income.source.ilike(term), Income.note.ilike(term)))
        expense_query = expense_query.filter(db.or_(Expense.category.ilike(term), Expense.note.ilike(term)))

    total_income = db.session.query(db.func.coalesce(db.func.sum(income_query.subquery().c.amount), 0)).scalar() or 0
    total_expense = db.session.query(db.func.coalesce(db.func.sum(expense_query.subquery().c.amount), 0)).scalar() or 0

    category_rows = (
        expense_query.with_entities(Expense.category, db.func.coalesce(db.func.sum(Expense.amount), 0))
        .group_by(Expense.category)
        .all()
    )
    categories = [{"category": c or "Other", "amount": float(a)} for c, a in category_rows]

    summary = {
        "income": float(total_income),
        "expense": float(total_expense),
        "balance": float(total_income) - float(total_expense),
    }

    return render_template("reports.html", summary=summary, categories=categories, form=form, q=q)


@finance_bp.route("/reports/export", methods=["GET"])
@login_required
def export_reports():
    uid = current_user.id
    validate_user_context(uid, raise_error=True)

    month = request.args.get("month") or datetime.now(UTC).strftime("%Y-%m")
    fmt = (request.args.get("format") or "csv").lower()
    start, end = _month_bounds(month)

    incomes = (
        Income.query.filter(Income.user_id == uid, Income.date >= start, Income.date < end)
        .order_by(Income.date.asc())
        .all()
    )
    expenses = (
        Expense.query.filter(Expense.user_id == uid, Expense.date >= start, Expense.date < end)
        .order_by(Expense.date.asc())
        .all()
    )

    if fmt == "csv":
        out = StringIO()
        out.write("type,date,amount,category_or_source,note\n")
        for i in incomes:
            out.write(f'income,{i.date},{float(i.amount):.2f},"{i.source}","{i.note or ""}"\n')
        for e in expenses:
            out.write(f'expense,{e.date},{float(e.amount):.2f},"{e.category}","{e.note or ""}"\n')
        return Response(
            out.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=report-{month}.csv"},
        )

    lines: List[str] = [f"Month: {month}", "", "Income"]
    for i in incomes:
        lines.append(f"{i.date} | {i.source} | PHP {float(i.amount):.2f}")
    lines.append("")
    lines.append("Expenses")
    for e in expenses:
        lines.append(f"{e.date} | {e.category} | PHP {float(e.amount):.2f}")

    total_income = sum(float(i.amount) for i in incomes)
    total_expense = sum(float(e.amount) for e in expenses)
    lines.append("")
    lines.append(f"Total Income: PHP {total_income:.2f}")
    lines.append(f"Total Expense: PHP {total_expense:.2f}")
    lines.append(f"Balance: PHP {total_income - total_expense:.2f}")

    pdf = _simple_pdf_bytes(f"PinkLedger Monthly Report - {month}", lines)
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report-{month}.pdf"},
    )
