import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-prod"


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

    raw_name = session.get("user_name", "User")
    parts = raw_name.split()
    initials = parts[0][0].upper() + (parts[-1][0].upper() if len(parts) > 1 else "")

    user = {
        "name": raw_name,
        "initials": initials,
        "email": session.get("user_email", ""),
        "joined": "January 12, 2025",
    }

    stats = {
        "total_spent": "₹24,580",
        "transaction_count": 47,
        "top_category": "Food",
    }

    transactions = [
        {"date": "May 2, 2025", "description": "Swiggy dinner order", "category": "Food", "amount": "₹540"},
        {"date": "Apr 29, 2025", "description": "Metro card recharge", "category": "Travel", "amount": "₹200"},
        {"date": "Apr 27, 2025", "description": "Amazon — earbuds", "category": "Shopping", "amount": "₹1,299"},
        {"date": "Apr 25, 2025", "description": "Electricity bill", "category": "Bills", "amount": "₹1,840"},
        {"date": "Apr 22, 2025", "description": "BookMyShow — movie", "category": "Entertainment", "amount": "₹450"},
    ]

    categories = [
        {"name": "Food", "amount": "₹8,240", "percent": 34},
        {"name": "Shopping", "amount": "₹6,580", "percent": 27},
        {"name": "Bills", "amount": "₹5,320", "percent": 22},
        {"name": "Travel", "amount": "₹2,740", "percent": 11},
        {"name": "Entertainment", "amount": "₹1,700", "percent": 7},
    ]

    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses")
def expenses():
    return "Expense list — coming in Step 5"


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
