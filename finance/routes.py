from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from finflow.app import db
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


def _parse_amount(value: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    if value is None:
        return None, "Amount is required"
    try:
        return float(value), None
    except (ValueError, TypeError):
        return None, "Invalid amount"


# ===== Dashboard =====
@finance_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Render dashboard (HTML) or return JSON summary depending on Accept header.
    Delegates business logic to the service layer when available.
    """
    uid = current_user.id

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
    Accepts form-submitted or JSON income data.
    Uses service layer if available; otherwise performs a small inline create.
    """
    uid = current_user.id
    data = request.get_json(silent=True) or request.form

    amount, err = _parse_amount(data.get("amount"))
    if err:
        flash(err, "danger")
        return redirect(url_for("finance.dashboard"))

    source = (data.get("source") or "").strip() or "Unknown"
    date_str = data.get("date")
    try:
        date_val = datetime.fromisoformat(date_str).date() if date_str else None
    except Exception:
        date_val = None

    if svc and hasattr(svc, "create_income"):
        inc = svc.create_income(uid, amount, source, date_val)
    else:
        from finflow.finance.models import Income  # type: ignore

        inc = Income(
            user_id=uid,
            amount=amount,
            source=source,
            date=date_val or datetime.utcnow(),
        )
        db.session.add(inc)
        db.session.commit()

    if request.is_json:
        return jsonify(
            {"status": "created", "income": getattr(inc, "to_dict", lambda: {})()}
        ), 201

    flash("Income added.", "success")
    return redirect(url_for("finance.dashboard"))


@finance_bp.route("/income", methods=["GET"])
@login_required
def list_incomes():
    """Return list of incomes for the current user as JSON."""
    uid = current_user.id
    if svc and hasattr(svc, "list_incomes"):
        items = svc.list_incomes(uid)
    else:
        from finflow.finance.models import Income  # type: ignore

        items = (
            Income.query.filter_by(user_id=uid)
            .order_by(Income.date.desc())
            .limit(current_app.config.get("DEFAULT_PAGE_SIZE", 50))
            .all()
        )
    # Ensure JSON-serializable
    return jsonify(
        [getattr(i, "to_dict", lambda: {"id": getattr(i, "id", None)})() for i in items]
    )


@finance_bp.route("/income/list", methods=["GET"])
@login_required
def income_page():
    uid = current_user.id
    from finflow.finance.models import Income  # type: ignore

    items = (
        Income.query.filter_by(user_id=uid)
        .order_by(Income.date.desc())
        .limit(current_app.config.get("DEFAULT_PAGE_SIZE", 50))
        .all()
    )
    return render_template(
        "income.html",
        incomes=items,
        today=datetime.utcnow().date().isoformat(),
    )


@finance_bp.route("/income/<int:item_id>", methods=["DELETE"])
@login_required
def delete_income(item_id: int):
    uid = current_user.id
    if svc and hasattr(svc, "delete_income"):
        ok = svc.delete_income(uid, item_id)
        status = 200 if ok else 403
        return jsonify({"deleted": ok}), status
    else:
        from finflow.finance.models import Income  # type: ignore

        inc = Income.query.get_or_404(item_id)
        if inc.user_id != uid:
            return jsonify({"error": "not authorized"}), 403
        db.session.delete(inc)
        db.session.commit()
        return jsonify({"deleted": True}), 200


# ===== Expense endpoints =====
@finance_bp.route("/expense", methods=["POST"])
@login_required
def add_expense():
    uid = current_user.id
    data = request.get_json(silent=True) or request.form

    amount, err = _parse_amount(data.get("amount"))
    if err:
        flash(err, "danger")
        return redirect(url_for("finance.dashboard"))

    category = (data.get("category") or "").strip() or "Others"
    date_str = data.get("date")
    try:
        date_val = datetime.fromisoformat(date_str).date() if date_str else None
    except Exception:
        date_val = None

    if svc and hasattr(svc, "create_expense"):
        exp = svc.create_expense(uid, amount, category, date_val)
    else:
        from finflow.finance.models import Expense  # type: ignore

        exp = Expense(
            user_id=uid,
            amount=amount,
            category=category,
            date=date_val or datetime.utcnow(),
        )
        db.session.add(exp)
        db.session.commit()

    if request.is_json:
        return jsonify(
            {"status": "created", "expense": getattr(exp, "to_dict", lambda: {})()}
        ), 201

    flash("Expense added.", "success")
    return redirect(url_for("finance.dashboard"))


@finance_bp.route("/expense", methods=["GET"])
@login_required
def list_expenses():
    uid = current_user.id
    if svc and hasattr(svc, "list_expenses"):
        items = svc.list_expenses(uid)
    else:
        from finflow.finance.models import Expense  # type: ignore

        items = (
            Expense.query.filter_by(user_id=uid)
            .order_by(Expense.date.desc())
            .limit(current_app.config.get("DEFAULT_PAGE_SIZE", 50))
            .all()
        )
    return jsonify(
        [getattr(e, "to_dict", lambda: {"id": getattr(e, "id", None)})() for e in items]
    )


@finance_bp.route("/expense/list", methods=["GET"])
@login_required
def expense_page():
    uid = current_user.id
    from finflow.finance.models import Expense  # type: ignore

    items = (
        Expense.query.filter_by(user_id=uid)
        .order_by(Expense.date.desc())
        .limit(current_app.config.get("DEFAULT_PAGE_SIZE", 50))
        .all()
    )
    return render_template(
        "expense.html",
        expenses=items,
        today=datetime.utcnow().date().isoformat(),
    )


@finance_bp.route("/expense/<int:item_id>", methods=["DELETE"])
@login_required
def delete_expense(item_id: int):
    uid = current_user.id
    if svc and hasattr(svc, "delete_expense"):
        ok = svc.delete_expense(uid, item_id)
        status = 200 if ok else 403
        return jsonify({"deleted": ok}), status
    else:
        from finflow.finance.models import Expense  # type: ignore

        exp = Expense.query.get_or_404(item_id)
        if exp.user_id != uid:
            return jsonify({"error": "not authorized"}), 403
        db.session.delete(exp)
        db.session.commit()
        return jsonify({"deleted": True}), 200


# ===== Budget =====
@finance_bp.route("/budget", methods=["GET"])
@login_required
def budget_page():
    uid = current_user.id
    month = request.args.get("month") or datetime.utcnow().strftime("%Y-%m")

    if svc and hasattr(svc, "get_budget"):
        b = svc.get_budget(uid, month)
    else:
        from finflow.finance.models import Budget  # type: ignore

        b = Budget.query.filter_by(user_id=uid, month=month).first()

    return render_template("budget.html", budget=b, current_month=month)


@finance_bp.route("/budget", methods=["POST"])
@login_required
def set_budget():
    uid = current_user.id
    data = request.get_json(silent=True) or request.form
    month = (data.get("month") or "").strip()
    amount, err = _parse_amount(data.get("amount"))
    if err:
        flash(err, "danger")
        return redirect(url_for("finance.dashboard"))

    if svc and hasattr(svc, "set_budget"):
        b = svc.set_budget(uid, month, amount)
    else:
        from finflow.finance.models import Budget  # type: ignore

        b = Budget.query.filter_by(user_id=uid, month=month).first()
        if not b:
            b = Budget(user_id=uid, month=month, amount=amount)
            db.session.add(b)
        else:
            b.amount = amount
        db.session.commit()

    if request.is_json:
        return jsonify(
            {"status": "ok", "budget": getattr(b, "to_dict", lambda: {})()}
        ), 200

    flash("Budget set.", "success")
    return redirect(url_for("finance.dashboard"))


# ===== Simple API: summary for charts =====
@finance_bp.route("/api/summary")
@login_required
def api_summary():
    uid = current_user.id
    if svc and hasattr(svc, "get_summary"):
        summary = svc.get_summary(uid)
    else:
        from finflow.finance.models import Expense, Income  # type: ignore

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
    uid = current_user.id
    if svc and hasattr(svc, "get_totals"):
        summary = svc.get_totals(uid)
    else:
        from finflow.finance.models import Expense, Income  # type: ignore

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
        from finflow.finance.models import Expense  # type: ignore

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
