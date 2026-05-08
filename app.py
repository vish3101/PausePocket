import sqlite3
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-prod"


def _resolve_date_filter(args) -> tuple[str, str, str, str]:
    today = date.today()
    # No default: None means "no period param" so bare from/to can still reach the custom check.
    period = args.get("period")

    # Named presets are checked first so clicking a preset button always wins,
    # even if stale from/to values are still present in the submitted form.
    if period == "this_month":
        df = today.replace(day=1)
        return df.isoformat(), today.isoformat(), period, today.strftime("%B %Y")

    if period == "last_month":
        first_of_this = today.replace(day=1)
        last_of_prev = first_of_this - timedelta(days=1)
        df = last_of_prev.replace(day=1)
        return df.isoformat(), last_of_prev.isoformat(), period, last_of_prev.strftime("%B %Y")

    if period == "last_3_months":
        df = today - timedelta(days=90)
        label = f"{fmt_date(df.isoformat())} – {fmt_date(today.isoformat())}"
        return df.isoformat(), today.isoformat(), period, label

    if period == "last_6_months":
        df = today - timedelta(days=180)
        label = f"{fmt_date(df.isoformat())} – {fmt_date(today.isoformat())}"
        return df.isoformat(), today.isoformat(), period, label

    if period == "all_time":
        return "0001-01-01", today.isoformat(), "all_time", "All Time"

    # No named preset matched — try custom from/to (submitted by the Apply button).
    custom_from = args.get("from", "").strip()
    custom_to = args.get("to", "").strip()
    if custom_from and custom_to:
        try:
            df = date.fromisoformat(custom_from)
            dt = date.fromisoformat(custom_to)
            label = f"{fmt_date(df.isoformat())} – {fmt_date(dt.isoformat())}"
            return df.isoformat(), dt.isoformat(), "custom", label
        except ValueError:
            pass

    return "0001-01-01", today.isoformat(), "all_time", "All Time"


def fmt_amount(amount: float) -> str:
    return f"₹{amount:,.0f}"


def fmt_date(iso: str) -> str:
    d = datetime.strptime(iso[:10], "%Y-%m-%d")
    return f"{d.strftime('%b')} {d.day}, {d.year}"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Full name is required.", name=name, email=email)
    if not email:
        return render_template("register.html", error="Email address is required.", name=name, email=email)
    if not password:
        return render_template("register.html", error="Password is required.", name=name, email=email)
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.", name=name, email=email)

    password_hash = generate_password_hash(password)

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.", name=name, email=email)

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = email
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    date_from, date_to, period, active_period = _resolve_date_filter(request.args)
    user_id = session["user_id"]

    with get_db() as conn:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        expense_rows = conn.execute(
            "SELECT amount, category, date, description FROM expenses "
            "WHERE user_id = ? AND date BETWEEN ? AND ? ORDER BY date DESC",
            (user_id, date_from, date_to),
        ).fetchall()

    parts = row["name"].split()
    initials = parts[0][0].upper() + (parts[-1][0].upper() if len(parts) > 1 else "")

    user = {
        "name": row["name"],
        "initials": initials,
        "email": row["email"],
        "joined": fmt_date(row["created_at"]),
    }

    category_totals: dict[str, float] = {}
    for r in expense_rows:
        category_totals[r["category"]] = category_totals.get(r["category"], 0) + r["amount"]

    total = sum(r["amount"] for r in expense_rows)
    top_category = max(category_totals, key=lambda k: category_totals[k]) if category_totals else "—"

    stats = {
        "total_spent": fmt_amount(total),
        "transaction_count": len(expense_rows),
        "top_category": top_category,
    }

    transactions = [
        {
            "date": fmt_date(r["date"]),
            "description": r["description"] or "",
            "category": r["category"],
            "amount": fmt_amount(r["amount"]),
        }
        for r in expense_rows[:5]
    ]

    categories = [
        {
            "name": name,
            "amount": fmt_amount(amount),
            "percent": round(amount / total * 100) if total else 0,
        }
        for name, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    return render_template(
        "profile.html",
        user=user, stats=stats, transactions=transactions, categories=categories,
        period=period, date_from=date_from, date_to=date_to, active_period=active_period,
    )


@app.route("/expenses")
def expenses():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC",
            (user_id,),
        ).fetchall()

    expense_list = [
        {
            "id": r["id"],
            "date": fmt_date(r["date"]),
            "description": r["description"] or "",
            "category": r["category"],
            "amount_fmt": fmt_amount(r["amount"]),
        }
        for r in rows
    ]

    category_totals: dict[str, float] = {}
    for r in rows:
        category_totals[r["category"]] = category_totals.get(r["category"], 0) + r["amount"]

    total = sum(r["amount"] for r in rows)
    top_category = max(category_totals, key=lambda k: category_totals[k]) if category_totals else "—"

    stats = {
        "total_spent": fmt_amount(total),
        "transaction_count": len(rows),
        "top_category": top_category,
    }

    categories = [
        {
            "name": name,
            "amount_fmt": fmt_amount(amount),
            "percent": round(amount / total * 100) if total else 0,
        }
        for name, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    return render_template("expenses.html", expenses=expense_list, stats=stats, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
