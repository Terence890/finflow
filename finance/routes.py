from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from finflow.app import db
from finflow.common.logger import finance_logger, log_transaction
from finflow.common.pagination import Paginator, get_page_from_request, get_per_page_from_request
from finflow.common.permissions import ensure_user_owns_data, validate_user_context
from finflow.finance.forms import (
    IncomeForm,
    ExpenseForm,
    BudgetForm,
    DateRangeForm,
)
from finflow.finance.models import Income, Expense, Budget
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

finance_bp = Blueprint(
    "finance", __name__, template_folder="../templates", static_folder="../static"
)


# Try to use a service layer if present to keep routes concise. If the service module
# is missing (early dev), fall back to small inline implementations that call models.
try:
    from finflow.finance import service as svc  # type: ignore
except Exception:
    svc = None  # type: ignore


# ===== Dashboard =====
@finance_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Render dashboard (HTML) or return JSON summary depending on Accept header.
    Delegates business logic to the service layer when available.
    """
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    finance_logger.info(f"User {uid} accessed dashboard")

    if svc and hasattr(svc, "get_dashboard_context"):
        ctx = svc.get_dashboard_context(uid)
    else:
        # Minimal inline fallback implementation using models (keeps routes usable)
        from finflow.finance.models import Budget, Expense, Income  # type: ignore

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
            Income.query.filter_by(user_id=uid)
            .order_by(Income.date.desc())
            .limit(5)
            .all()
        )
        expenses = (
            Expense.query.filter_by(user_id=uid)
            .order_by(Expense.date.desc())
            .limit(5)
            .all()
        )
        # Simple category aggregation
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
        ctx = {
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "balance": float(balance),
            "incomes": incomes,
            "expenses": expenses,
            "categories": categories,
        }

    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        return jsonify(ctx)

    # Render template; templates expect certain variables
    return render_template(
        "dashboard.html",
        total_income=ctx.get("total_income", 0),
        total_expense=ctx.get("total_expense", 0),
        balance=ctx.get("balance", 0),
        incomes=ctx.get("incomes", []),
        expenses=ctx.get("expenses", []),
        expense_by_category=ctx.get("categories", []),
        today=datetime.utcnow().date().isoformat(),
    )


# ===== Income endpoints (form + API) =====
@finance_bp.route("/income", methods=["POST"])
@login_required
def add_income():
    """
    Create income from form/JSON data using WTF forms validation.
    """
    uid = current_user.id
    form = IncomeForm()
    
    if not form.validate_on_submit():
        flash("Invalid income data. Please check your input.", "danger")
        return redirect(url_for("finance.income_page"))
    
    try:
        income = Income(
            user_id=uid,
            amount=form.amount.data,
            source=form.source.data.strip(),
            date=form.date.data or datetime.utcnow().date(),
            note=form.note.data.strip() if form.note.data else None,
        )
        db.session.add(income)
        db.session.commit()
        
        log_transaction(uid, "income", form.source.data, float(form.amount.data))
        flash("Income added successfully!", "success")
        
        if request.is_json:
            return jsonify({"status": "created", "income": income.to_dict()}), 201
        return redirect(url_for("finance.income_page"))
    except Exception as e:
        db.session.rollback()
        finance_logger.error(f"Failed to add income for user {uid}: {str(e)}")
        flash("Failed to add income. Please try again.", "danger")
        return redirect(url_for("finance.income_page")) if not request.is_json else jsonify({"error": "Failed to create income"}), 500


@finance_bp.route("/income", methods=["GET"])
@login_required
def list_incomes():
    """Return list of incomes for the current user as JSON with pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    
    page = get_page_from_request()
    per_page = get_per_page_from_request()
    
    query = Income.query.filter_by(user_id=uid).order_by(Income.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()
    
    return jsonify({
        "incomes": [i.to_dict() for i in items],
        "pagination": paginator.to_dict()
    })


@finance_bp.route("/income/list", methods=["GET"])
@login_required
def income_page():
    """Display income list with pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    
    page = get_page_from_request()
    per_page = get_per_page_from_request()
    
    query = Income.query.filter_by(user_id=uid).order_by(Income.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()
    
    finance_logger.info(f"User {uid} viewed income list (page {page}, per_page {per_page})")
    
    return render_template(
        "income.html",
        incomes=items,
        paginator=paginator,
        today=datetime.utcnow().date().isoformat(),
    )


@finance_bp.route("/income/<int:item_id>", methods=["DELETE"])
@login_required
def delete_income(item_id: int):
    """Delete an income record with permission validation."""
    uid = current_user.id
    
    income = Income.query.get_or_404(item_id)
    
    # Validate user owns this income before deletion
    if not ensure_user_owns_data(income, raise_error=False):
        finance_logger.warning(f"User {uid} attempted to delete income {item_id} they don't own")
        return jsonify({"error": "Forbidden"}), 403
    
    try:
        amount = float(income.amount)
        db.session.delete(income)
        db.session.commit()
        
        log_transaction(uid, "income_delete", income.source, amount, status="success")
        return jsonify({"deleted": True}), 200
    except Exception as e:
        db.session.rollback()
        finance_logger.error(f"Failed to delete income {item_id} for user {uid}: {str(e)}")
        return jsonify({"error": "Failed to delete income"}), 500


# ===== Expense endpoints =====
@finance_bp.route("/expense", methods=["POST"])
@login_required
def add_expense():
    """Create expense from form/JSON data using WTF forms validation."""
    uid = current_user.id
    form = ExpenseForm()
    
    if not form.validate_on_submit():
        flash("Invalid expense data. Please check your input.", "danger")
        return redirect(url_for("finance.expense_page"))
    
    try:
        expense = Expense(
            user_id=uid,
            amount=form.amount.data,
            category=form.category.data,
            date=form.date.data or datetime.utcnow().date(),
            note=form.description.data.strip() if form.description.data else None,
        )
        db.session.add(expense)
        db.session.commit()
        
        log_transaction(uid, "expense", form.category.data, float(form.amount.data))
        flash("Expense added successfully!", "success")
        
        if request.is_json:
            return jsonify({"status": "created", "expense": expense.to_dict()}), 201
        return redirect(url_for("finance.expense_page"))
    except Exception as e:
        db.session.rollback()
        finance_logger.error(f"Failed to add expense for user {uid}: {str(e)}")
        flash("Failed to add expense. Please try again.", "danger")
        return redirect(url_for("finance.expense_page")) if not request.is_json else jsonify({"error": "Failed to create expense"}), 500


@finance_bp.route("/expense", methods=["GET"])
@login_required
def list_expenses():
    """Return list of expenses for the current user as JSON with pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    
    page = get_page_from_request()
    per_page = get_per_page_from_request()
    
    query = Expense.query.filter_by(user_id=uid).order_by(Expense.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()
    
    return jsonify({
        "expenses": [e.to_dict() for e in items],
        "pagination": paginator.to_dict()
    })


@finance_bp.route("/expense/list", methods=["GET"])
@login_required
def expense_page():
    """Display expense list with pagination."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    
    page = get_page_from_request()
    per_page = get_per_page_from_request()
    
    query = Expense.query.filter_by(user_id=uid).order_by(Expense.date.desc())
    paginator = Paginator(query, page=page, per_page=per_page)
    items = paginator.get_items()
    
    finance_logger.info(f"User {uid} viewed expense list (page {page}, per_page {per_page})")
    
    return render_template(
        "expense.html",
        expenses=items,
        paginator=paginator,
        today=datetime.utcnow().date().isoformat(),
    )


@finance_bp.route("/expense/<int:item_id>", methods=["DELETE"])
@login_required
def delete_expense(item_id: int):
    """Delete an expense record with permission validation."""
    uid = current_user.id
    
    expense = Expense.query.get_or_404(item_id)
    
    # Validate user owns this expense before deletion
    if not ensure_user_owns_data(expense, raise_error=False):
        finance_logger.warning(f"User {uid} attempted to delete expense {item_id} they don't own")
        return jsonify({"error": "Forbidden"}), 403
    
    try:
        amount = float(expense.amount)
        db.session.delete(expense)
        db.session.commit()
        
        log_transaction(uid, "expense_delete", expense.category, amount, status="success")
        return jsonify({"deleted": True}), 200
    except Exception as e:
        db.session.rollback()
        finance_logger.error(f"Failed to delete expense {item_id} for user {uid}: {str(e)}")
        return jsonify({"error": "Failed to delete expense"}), 500


# ===== Budget =====
@finance_bp.route("/budget", methods=["GET"])
@login_required
def budget_page():
    """Display budget page for current month."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    
    month = request.args.get("month") or datetime.utcnow().strftime("%Y-%m")
    finance_logger.info(f"User {uid} viewed budget for month {month}")

    if svc and hasattr(svc, "get_budget"):
        b = svc.get_budget(uid, month)
    else:
        b = Budget.query.filter_by(user_id=uid, month=month).first()

    return render_template("budget.html", budget=b, current_month=month)


@finance_bp.route("/budget", methods=["POST"])
@login_required
def set_budget():
    """Set budget for a month using WTF form."""
    uid = current_user.id
    form = BudgetForm()
    
    if not form.validate_on_submit():
        flash("Invalid budget data. Please check your input.", "danger")
        return redirect(url_for("finance.budget_page"))
    
    month = request.args.get("month") or datetime.utcnow().strftime("%Y-%m")
    
    try:
        b = Budget.query.filter_by(user_id=uid, month=month).first()
        if not b:
            b = Budget(user_id=uid, month=month, amount=form.limit.data)
            db.session.add(b)
        else:
            b.amount = form.limit.data
        db.session.commit()
        
        log_transaction(uid, "budget_set", "monthly", float(form.limit.data))
        flash("Budget set successfully!", "success")
        
        if request.is_json:
            return jsonify({"status": "ok", "budget": b.to_dict()}), 200
        return redirect(url_for("finance.budget_page"))
    except Exception as e:
        db.session.rollback()
        finance_logger.error(f"Failed to set budget for user {uid} month {month}: {str(e)}")
        flash("Failed to set budget. Please try again.", "danger")
        return redirect(url_for("finance.budget_page")) if not request.is_json else jsonify({"error": "Failed to set budget"}), 500


# ===== Simple API: summary for charts =====
@finance_bp.route("/api/summary")
@login_required
def api_summary():
    """Get financial summary for current user."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    finance_logger.info(f"User {uid} accessed API summary")
    
    if svc and hasattr(svc, "get_summary"):
        summary = svc.get_summary(uid)
    else:
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
        summary = {"income": float(total_income), "expense": float(total_expense)}
    return jsonify(summary)


@finance_bp.route("/reports", methods=["GET"])
@login_required
def reports_page():
    """Display financial reports page."""
    uid = current_user.id
    validate_user_context(uid, raise_error=True)
    finance_logger.info(f"User {uid} accessed reports page")
    
    if svc and hasattr(svc, "get_totals"):
        summary = svc.get_totals(uid)
    else:
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
        summary = {
            "income": float(total_income),
            "expense": float(total_expense),
            "balance": float(total_income) - float(total_expense),
        }

    if svc and hasattr(svc, "expense_by_category"):
        categories = svc.expense_by_category(uid)
    else:
        rows = (
            db.session.query(
                Expense.category, db.func.coalesce(db.func.sum(Expense.amount), 0)
            )
            .filter(Expense.user_id == uid)
            .group_by(Expense.category)
            .all()
        )
        categories = [
            {"category": c or "Other", "amount": float(a)} for c, a in rows
        ]

    return render_template(
        "reports.html",
        summary=summary,
        categories=categories,
    )
