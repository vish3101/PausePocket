import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "expense_tracker.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                description TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)


def seed_db() -> None:
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        uid = cur.lastrowid

        expenses = [
            (uid, 320.00,  "Food",          "2026-04-02", "Groceries"),
            (uid, 150.00,  "Transport",     "2026-04-05", "Metro card top-up"),
            (uid, 1200.00, "Bills",         "2026-04-08", "Electricity bill"),
            (uid, 500.00,  "Health",        "2026-04-10", "Pharmacy"),
            (uid, 350.00,  "Entertainment", "2026-04-14", "Movie tickets"),
            (uid, 899.00,  "Shopping",      "2026-04-18", "Shirt"),
            (uid, 75.00,   "Food",          "2026-04-22", "Coffee and snacks"),
            (uid, 200.00,  "Other",         "2026-04-27", "Stationery"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
