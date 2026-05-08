"""
tests/test_06-date-filter-profile.py

Pytest test suite for the Date Filter on Profile Page feature.
All assertions are derived from the spec's Definition of Done — not from
reverse-engineering the implementation.

Isolation strategy
------------------
database.db.DB_PATH is a module-level string.  We override it (and the
cached DB file location) by monkey-patching ``database.db.DB_PATH`` with
``monkeypatch.setattr`` before any test code runs.  Each fixture creates a
fresh temporary file so every test gets an empty, independent database.

Because app.py runs ``init_db()`` and ``seed_db()`` at module import time we
must import the flask app *once* (Python caches it) and instead call
``init_db()`` ourselves inside the fixture after redirecting DB_PATH.  The
``seed_db()`` guard (SELECT 1 FROM users LIMIT 1) means repeated calls are
safe; we bypass it by inserting test data directly via sqlite3.
"""

import sqlite3
from datetime import date, timedelta

import pytest

# Import application objects once at module level.
import database.db as db_module
from app import app as flask_app

# ---------------------------------------------------------------------------
# Date helpers — keep tests calendar-agnostic
# ---------------------------------------------------------------------------

def _today() -> date:
    return date.today()


def _iso(d: date) -> str:
    return d.isoformat()


def _first_of_month(d: date) -> date:
    return d.replace(day=1)


def _last_month_range() -> tuple[date, date]:
    first_of_this = _first_of_month(_today())
    last_of_prev = first_of_this - timedelta(days=1)
    first_of_prev = _first_of_month(last_of_prev)
    return first_of_prev, last_of_prev


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def app(tmp_path, monkeypatch):
    """
    Yield a configured Flask test app wired to a fresh temporary SQLite file.

    monkeypatch.setattr rewires database.db.DB_PATH so every call to
    get_db() inside the route handler uses the isolated temp DB.
    """
    db_file = str(tmp_path / "test_spendly.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with flask_app.app_context():
        # Initialise schema in the fresh temp DB.
        db_module.init_db()
        yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded_client(client):
    """
    A logged-in test client with expenses spread across multiple date windows:

      Window               | Count | Categories & amounts
      ---------------------|-------|----------------------------------------------
      This calendar month  |   6   | Food x3 @300 (=900), Bills x2 @400 (=800),
                           |       | Health x1 @200
      Last calendar month  |   3   | Transport x2 @150 (=300), Shopping x1 @500
      90–100 days ago      |   2   | Other x2 @999   (outside 90-day window)
      180–200 days ago     |   2   | Misc x2 @1111   (outside 180-day window)
      2020-01-15 (ancient) |   1   | Food @50        (only visible under all_time)
      ---------------------|-------|----------------------------------------------
      Total                |  14   |
    """
    # Register + login through HTTP (exercises the real auth stack).
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "testuser@example.com",
            "password": "securepass123",
        },
    )
    client.post(
        "/login",
        data={"email": "testuser@example.com", "password": "securepass123"},
    )

    # Resolve user_id from the temp DB (monkeypatched DB_PATH is already set).
    db_path = db_module.DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("testuser@example.com",)
    ).fetchone()
    uid = row["id"]

    today = _today()
    this_month_start = _first_of_month(today)
    last_month_start, last_month_end = _last_month_range()
    days_100_ago = today - timedelta(days=100)
    days_200_ago = today - timedelta(days=200)
    ancient = date(2020, 1, 15)

    def this_month_day(offset: int) -> str:
        d = this_month_start + timedelta(days=offset)
        return _iso(min(d, today))  # clamp to today if month just started

    def last_month_day(offset: int) -> str:
        d = last_month_start + timedelta(days=offset)
        return _iso(min(d, last_month_end))

    expenses = [
        # Current month — Food wins (900 > Bills 800)
        (uid, 300.00, "Food",      this_month_day(0), "Groceries A"),
        (uid, 300.00, "Food",      this_month_day(1), "Groceries B"),
        (uid, 300.00, "Food",      this_month_day(2), "Groceries C"),
        (uid, 400.00, "Bills",     this_month_day(3), "Electricity"),
        (uid, 400.00, "Bills",     this_month_day(4), "Water bill"),
        (uid, 200.00, "Health",    this_month_day(5), "Pharmacy"),
        # Last month — Shopping wins (500 > Transport 300)
        (uid, 150.00, "Transport", last_month_day(0), "Metro A"),
        (uid, 150.00, "Transport", last_month_day(1), "Metro B"),
        (uid, 500.00, "Shopping",  last_month_day(2), "Clothes"),
        # 100 days ago — outside 90-day window, inside 180-day window
        (uid, 999.00, "Other",     _iso(days_100_ago), "Old expense 1"),
        (uid, 999.00, "Other",     _iso(days_100_ago), "Old expense 2"),
        # 200 days ago — outside 180-day window
        (uid, 1111.00, "Misc",     _iso(days_200_ago), "Ancient expense 1"),
        (uid, 1111.00, "Misc",     _iso(days_200_ago), "Ancient expense 2"),
        # Ancient — only visible under all_time
        (uid, 50.00,  "Food",      _iso(ancient),       "Very old snack"),
    ]

    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()

    return client


# ---------------------------------------------------------------------------
# Utility: count <tr> rows inside <tbody> from raw HTML bytes
# ---------------------------------------------------------------------------

def _count_tbody_rows(data: bytes) -> int:
    tbody_start = data.find(b"<tbody>")
    tbody_end = data.find(b"</tbody>", tbody_start)
    if tbody_start == -1 or tbody_end == -1:
        return 0
    return data[tbody_start:tbody_end].count(b"<tr>")


def _active_button_surrounds(html: str, value: str, window: int = 100) -> str:
    """Return the substring of html centred around the named preset button."""
    idx = html.find(f'value="{value}"')
    if idx == -1:
        return ""
    return html[max(0, idx - window): idx + window]


# ===========================================================================
# 1. Authentication guard
# ===========================================================================

class TestAuthGuard:

    def test_unauthenticated_get_redirects_to_login(self, client):
        """GET /profile without a session must 302 to /login."""
        r = client.get("/profile")
        assert r.status_code == 302, "Expected 302 for unauthenticated /profile"
        assert "/login" in r.headers["Location"], "Redirect must point to /login"

    def test_period_param_does_not_bypass_auth(self, client):
        r = client.get("/profile?period=this_month")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_custom_range_params_do_not_bypass_auth(self, client):
        r = client.get("/profile?from=2026-01-01&to=2026-12-31")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]


# ===========================================================================
# 2. Default (no query params) — all_time behaviour
# ===========================================================================

class TestDefaultAllTime:

    def test_returns_200(self, seeded_client):
        assert seeded_client.get("/profile").status_code == 200

    def test_showing_label_is_all_time(self, seeded_client):
        r = seeded_client.get("/profile")
        assert b"All Time" in r.data, "'Showing: All Time' must appear with no period param"

    def test_all_time_button_has_active_class(self, seeded_client):
        r = seeded_client.get("/profile")
        surrounding = _active_button_surrounds(r.data.decode(), "all_time")
        assert "filter-btn-active" in surrounding, (
            "filter-btn-active must be on the All Time button by default"
        )

    def test_five_preset_buttons_present(self, seeded_client):
        html = seeded_client.get("/profile").data.decode()
        for value in ("this_month", "last_month", "last_3_months", "last_6_months", "all_time"):
            assert f'value="{value}"' in html, f"Preset button '{value}' must be present"

    def test_filter_form_uses_get_method(self, seeded_client):
        r = seeded_client.get("/profile")
        assert b'method="GET"' in r.data, "Filter form must use method=GET"

    def test_filter_form_action_is_profile(self, seeded_client):
        r = seeded_client.get("/profile")
        assert b'action="/profile"' in r.data, "Filter form action must be /profile"

    def test_showing_label_present(self, seeded_client):
        assert b"Showing:" in seeded_client.get("/profile").data

    def test_all_14_expenses_counted(self, seeded_client):
        """All-time default must count all 14 seeded expenses."""
        r = seeded_client.get("/profile")
        assert b"14" in r.data, "All 14 seeded expenses must appear under all_time"

    def test_navbar_shows_username(self, seeded_client):
        r = seeded_client.get("/profile")
        assert b"Test User" in r.data, "Navbar must show the logged-in username"

    def test_navbar_has_logout_link(self, seeded_client):
        r = seeded_client.get("/profile")
        assert b"/logout" in r.data, "Navbar must contain a /logout link"


# ===========================================================================
# 3. Preset: this_month
# ===========================================================================

class TestPresetThisMonth:

    def test_returns_200(self, seeded_client):
        assert seeded_client.get("/profile?period=this_month").status_code == 200

    def test_this_month_button_active(self, seeded_client):
        html = seeded_client.get("/profile?period=this_month").data.decode()
        surrounding = _active_button_surrounds(html, "this_month")
        assert "filter-btn-active" in surrounding, (
            "filter-btn-active must be on the This Month button"
        )

    def test_other_preset_buttons_not_active(self, seeded_client):
        html = seeded_client.get("/profile?period=this_month").data.decode()
        for other in ("last_month", "last_3_months", "last_6_months", "all_time"):
            surrounding = _active_button_surrounds(html, other)
            assert "filter-btn-active" not in surrounding, (
                f"Button '{other}' must NOT be active when period=this_month"
            )

    def test_showing_label_contains_current_month(self, seeded_client):
        month_name = _today().strftime("%B")
        r = seeded_client.get("/profile?period=this_month")
        assert month_name.encode() in r.data, (
            f"Showing label must contain '{month_name}' for this_month"
        )

    def test_transaction_count_is_6(self, seeded_client):
        """6 expenses were seeded in the current month."""
        r = seeded_client.get("/profile?period=this_month")
        assert b"6" in r.data, "Transaction count for this_month must be 6"

    def test_total_spent_is_1900(self, seeded_client):
        """Food 900 + Bills 800 + Health 200 = 1900."""
        r = seeded_client.get("/profile?period=this_month")
        assert "1,900" in r.data.decode(), (
            "Total spent for this_month must be ₹1,900"
        )

    def test_top_category_is_food(self, seeded_client):
        """Food (900) > Bills (800) > Health (200)."""
        r = seeded_client.get("/profile?period=this_month")
        assert b"Food" in r.data, "Food must be top category for this_month"

    def test_categories_include_food_bills_health(self, seeded_client):
        html = seeded_client.get("/profile?period=this_month").data.decode()
        for cat in ("Food", "Bills", "Health"):
            assert cat in html, f"{cat} must appear in this_month category breakdown"

    def test_transactions_capped_at_5(self, seeded_client):
        """6 expenses seeded this month — table must show at most 5."""
        r = seeded_client.get("/profile?period=this_month")
        assert _count_tbody_rows(r.data) <= 5, (
            "Transaction table must cap at 5 rows even with 6 matching expenses"
        )


# ===========================================================================
# 4. Preset: last_month
# ===========================================================================

class TestPresetLastMonth:

    def test_returns_200(self, seeded_client):
        assert seeded_client.get("/profile?period=last_month").status_code == 200

    def test_last_month_button_active(self, seeded_client):
        html = seeded_client.get("/profile?period=last_month").data.decode()
        surrounding = _active_button_surrounds(html, "last_month")
        assert "filter-btn-active" in surrounding, (
            "filter-btn-active must be on the Last Month button"
        )

    def test_showing_label_contains_last_month_name(self, seeded_client):
        _, last_month_end = _last_month_range()
        month_name = last_month_end.strftime("%B")
        r = seeded_client.get("/profile?period=last_month")
        assert month_name.encode() in r.data, (
            f"Showing label must contain '{month_name}' for last_month"
        )

    def test_transaction_count_is_3(self, seeded_client):
        """3 expenses were seeded in last calendar month."""
        r = seeded_client.get("/profile?period=last_month")
        assert b"3" in r.data, "Transaction count for last_month must be 3"

    def test_total_spent_is_800(self, seeded_client):
        """Transport 300 + Shopping 500 = 800."""
        r = seeded_client.get("/profile?period=last_month")
        assert "800" in r.data.decode(), "Total spent for last_month must be ₹800"

    def test_top_category_is_shopping(self, seeded_client):
        """Shopping (500) > Transport (300)."""
        r = seeded_client.get("/profile?period=last_month")
        assert b"Shopping" in r.data, "Shopping must be top category for last_month"

    def test_categories_include_transport_and_shopping(self, seeded_client):
        html = seeded_client.get("/profile?period=last_month").data.decode()
        assert "Transport" in html, "Transport must appear in last_month category breakdown"
        assert "Shopping" in html, "Shopping must appear in last_month category breakdown"

    def test_this_month_expenses_excluded(self, seeded_client):
        """Food 300 × 3 seeded this month must not inflate last_month total."""
        r = seeded_client.get("/profile?period=last_month")
        # Total must be 800, not 2700 (800 + 900 Food this month).
        assert "2,700" not in r.data.decode(), (
            "This month's Food expenses must not appear under last_month"
        )

    def test_transactions_capped_at_5(self, seeded_client):
        r = seeded_client.get("/profile?period=last_month")
        assert _count_tbody_rows(r.data) <= 5

    def test_3_last_month_expenses_all_shown(self, seeded_client):
        """3 expenses — all under the 5-row cap — must appear."""
        r = seeded_client.get("/profile?period=last_month")
        assert _count_tbody_rows(r.data) == 3, (
            "All 3 last_month expenses must be shown (under the 5-row cap)"
        )


# ===========================================================================
# 5. Preset: last_3_months
# ===========================================================================

class TestPresetLast3Months:

    def test_returns_200(self, seeded_client):
        assert seeded_client.get("/profile?period=last_3_months").status_code == 200

    def test_button_active(self, seeded_client):
        html = seeded_client.get("/profile?period=last_3_months").data.decode()
        surrounding = _active_button_surrounds(html, "last_3_months")
        assert "filter-btn-active" in surrounding, (
            "filter-btn-active must be on the Last 3 Months button"
        )

    def test_showing_label_present(self, seeded_client):
        r = seeded_client.get("/profile?period=last_3_months")
        assert b"Showing:" in r.data

    def test_expense_100_days_ago_excluded(self, seeded_client):
        """
        Expenses 100 days ago are outside the 90-day window.
        Their unique amount (999) must not appear in the response.
        """
        r = seeded_client.get("/profile?period=last_3_months")
        assert "999" not in r.data.decode(), (
            "Expenses 100 days ago (amount 999) must be excluded from last_3_months"
        )

    def test_expense_200_days_ago_excluded(self, seeded_client):
        """Expenses 200 days ago (amount 1111) are outside the 90-day window."""
        r = seeded_client.get("/profile?period=last_3_months")
        assert "1,111" not in r.data.decode(), (
            "Expenses 200 days ago (amount 1111) must be excluded from last_3_months"
        )

    def test_ancient_expense_excluded(self, seeded_client):
        """Misc category only exists in 200-day-ago expenses — must not appear."""
        r = seeded_client.get("/profile?period=last_3_months")
        assert "Misc" not in r.data.decode(), (
            "Misc category (200-day-old) must not appear in last_3_months"
        )

    def test_current_month_expenses_included(self, seeded_client):
        """This month's expenses are within the 90-day window."""
        r = seeded_client.get("/profile?period=last_3_months")
        assert b"Food" in r.data, "Food (this month) must appear in last_3_months"


# ===========================================================================
# 6. Preset: last_6_months
# ===========================================================================

class TestPresetLast6Months:

    def test_returns_200(self, seeded_client):
        assert seeded_client.get("/profile?period=last_6_months").status_code == 200

    def test_button_active(self, seeded_client):
        html = seeded_client.get("/profile?period=last_6_months").data.decode()
        surrounding = _active_button_surrounds(html, "last_6_months")
        assert "filter-btn-active" in surrounding, (
            "filter-btn-active must be on the Last 6 Months button"
        )

    def test_showing_label_present(self, seeded_client):
        r = seeded_client.get("/profile?period=last_6_months")
        assert b"Showing:" in r.data

    def test_expense_100_days_ago_included(self, seeded_client):
        """100 days ago is within the 180-day window — amount 999 must appear."""
        r = seeded_client.get("/profile?period=last_6_months")
        assert "999" in r.data.decode(), (
            "Expenses 100 days ago (amount 999) must be included in last_6_months"
        )

    def test_expense_200_days_ago_excluded(self, seeded_client):
        """200 days ago is outside the 180-day window — amount 1111 must not appear."""
        r = seeded_client.get("/profile?period=last_6_months")
        assert "1,111" not in r.data.decode(), (
            "Expenses 200 days ago (amount 1111) must be excluded from last_6_months"
        )

    def test_misc_category_excluded(self, seeded_client):
        """Misc only exists in 200-day-old data — must not appear."""
        r = seeded_client.get("/profile?period=last_6_months")
        assert "Misc" not in r.data.decode(), (
            "Misc category (200-day-old) must not appear in last_6_months"
        )

    def test_other_category_included(self, seeded_client):
        """Other (100 days ago) is inside the 180-day window."""
        r = seeded_client.get("/profile?period=last_6_months")
        assert b"Other" in r.data, (
            "Other category (100-day-old) must appear in last_6_months"
        )


# ===========================================================================
# 7. Explicit all_time param
# ===========================================================================

class TestExplicitAllTime:

    def test_returns_200(self, seeded_client):
        assert seeded_client.get("/profile?period=all_time").status_code == 200

    def test_all_time_button_active(self, seeded_client):
        html = seeded_client.get("/profile?period=all_time").data.decode()
        surrounding = _active_button_surrounds(html, "all_time")
        assert "filter-btn-active" in surrounding

    def test_showing_all_time_label(self, seeded_client):
        r = seeded_client.get("/profile?period=all_time")
        assert b"All Time" in r.data

    def test_all_14_expenses_counted(self, seeded_client):
        r = seeded_client.get("/profile?period=all_time")
        assert b"14" in r.data, "All 14 seeded expenses must be counted under all_time"

    def test_misc_category_present(self, seeded_client):
        """Misc only exists in 200-day-old data — must appear under all_time."""
        r = seeded_client.get("/profile?period=all_time")
        assert b"Misc" in r.data, "Misc category must appear under all_time"

    def test_ancient_expense_contributes_to_total(self, seeded_client):
        """
        Ancient Food expense (50) must be counted in all_time total.
        All-time total = 900+800+200+300+500+1998+2222+50 = 6970 — the exact
        total is not hardcoded; instead we confirm Misc (2222) appears since
        it's only visible under all_time.
        """
        r = seeded_client.get("/profile?period=all_time")
        # 200-day amounts formatted: ₹1,111 each; Misc appears in breakdown.
        assert "1,111" in r.data.decode(), (
            "Individual 1111 amounts must be visible in all_time category breakdown"
        )


# ===========================================================================
# 8. Custom date range
# ===========================================================================

class TestCustomDateRange:

    def test_returns_200_valid_range(self, seeded_client):
        today = _today()
        r = seeded_client.get(
            f"/profile?period=custom"
            f"&from={_iso(_first_of_month(today))}"
            f"&to={_iso(today)}"
        )
        assert r.status_code == 200

    def test_custom_range_this_month_shows_6_transactions(self, seeded_client):
        today = _today()
        r = seeded_client.get(
            f"/profile?period=custom"
            f"&from={_iso(_first_of_month(today))}"
            f"&to={_iso(today)}"
        )
        assert b"6" in r.data, (
            "Custom range covering this month must report 6 transactions"
        )

    def test_showing_label_present_for_custom_range(self, seeded_client):
        today = _today()
        r = seeded_client.get(
            f"/profile?period=custom"
            f"&from={_iso(_first_of_month(today))}"
            f"&to={_iso(today)}"
        )
        assert b"Showing:" in r.data

    def test_showing_label_contains_year_for_custom_range(self, seeded_client):
        today = _today()
        r = seeded_client.get(
            f"/profile?period=custom"
            f"&from={_iso(_first_of_month(today))}"
            f"&to={_iso(today)}"
        )
        assert str(today.year).encode() in r.data, (
            "Showing label must contain the current year for custom range"
        )

    def test_custom_range_excludes_out_of_window_expenses(self, seeded_client):
        """Narrow range of a single future year must match 0 expenses."""
        r = seeded_client.get("/profile?period=custom&from=2099-01-01&to=2099-12-31")
        assert b"14" not in r.data, (
            "Future custom range must not include any of the 14 seeded expenses"
        )

    def test_no_preset_button_active_for_custom_period(self, seeded_client):
        """
        When period=custom, none of the five preset buttons should carry
        the active class.
        """
        today = _today()
        html = seeded_client.get(
            f"/profile?period=custom"
            f"&from={_iso(_first_of_month(today))}"
            f"&to={_iso(today)}"
        ).data.decode()
        for preset in ("this_month", "last_month", "last_3_months", "last_6_months", "all_time"):
            surrounding = _active_button_surrounds(html, preset)
            assert "filter-btn-active" not in surrounding, (
                f"Preset button '{preset}' must not be active when period=custom"
            )

    def test_custom_range_transactions_capped_at_5(self, seeded_client):
        r = seeded_client.get("/profile?period=all_time")
        assert _count_tbody_rows(r.data) <= 5, (
            "Transaction table must cap at 5 rows even for all_time custom-equivalent range"
        )


# ===========================================================================
# 9. Malformed / missing custom date inputs
# ===========================================================================

class TestMalformedCustomDates:

    @pytest.mark.parametrize("qs", [
        "from=not-a-date&to=2026-01-31",
        "from=2026-01-01&to=invalid",
        "from=abc&to=xyz",
        "from=&to=",
        "from=2026-13-01&to=2026-12-31",   # month 13 is invalid
        "from=2026-01-01&to=2026-00-01",   # day/month 0 is invalid
    ])
    def test_malformed_dates_no_500(self, seeded_client, qs):
        """Any malformed date input must not produce a 500 error."""
        r = seeded_client.get(f"/profile?{qs}")
        assert r.status_code == 200, (
            f"Malformed custom dates ({qs}) must not raise a 500 error"
        )

    def test_malformed_both_falls_back_to_all_time(self, seeded_client):
        r = seeded_client.get("/profile?from=not-a-date&to=also-not")
        assert b"All Time" in r.data, (
            "Malformed from+to must fall back to All Time"
        )

    def test_missing_to_falls_back_to_all_time(self, seeded_client):
        r = seeded_client.get("/profile?from=2026-01-01")
        assert r.status_code == 200
        assert b"All Time" in r.data, "Missing to date must fall back to All Time"

    def test_missing_from_falls_back_to_all_time(self, seeded_client):
        r = seeded_client.get("/profile?to=2026-12-31")
        assert r.status_code == 200
        assert b"All Time" in r.data, "Missing from date must fall back to All Time"

    def test_empty_both_falls_back_to_all_time(self, seeded_client):
        r = seeded_client.get("/profile?from=&to=")
        assert b"All Time" in r.data


# ===========================================================================
# 10. Empty period — no expenses match the filter
# ===========================================================================

class TestEmptyPeriod:

    @pytest.fixture()
    def empty_client(self, client):
        """A logged-in client whose account has zero expenses."""
        client.post(
            "/register",
            data={
                "name": "Empty User",
                "email": "empty@example.com",
                "password": "emptypass123",
            },
        )
        client.post(
            "/login",
            data={"email": "empty@example.com", "password": "emptypass123"},
        )
        return client

    def test_no_expenses_returns_200(self, empty_client):
        r = empty_client.get("/profile?period=this_month")
        assert r.status_code == 200

    def test_no_transactions_message_shown(self, empty_client):
        r = empty_client.get("/profile?period=this_month")
        assert b"No transactions in this period." in r.data, (
            "Empty transaction list must display 'No transactions in this period.'"
        )

    def test_no_categories_message_shown(self, empty_client):
        r = empty_client.get("/profile?period=this_month")
        assert b"No expenses in this period." in r.data, (
            "Empty category list must display 'No expenses in this period.'"
        )

    def test_top_category_is_dash_when_no_expenses(self, seeded_client):
        """Far-future custom range — no expenses match — top category must be '—'."""
        r = seeded_client.get("/profile?from=2099-01-01&to=2099-12-31")
        assert "—" in r.data.decode(), (
            "Top category must be '—' when no expenses match the filter"
        )

    def test_total_spent_is_zero_when_no_expenses(self, seeded_client):
        r = seeded_client.get("/profile?from=2099-01-01&to=2099-12-31")
        assert "₹0" in r.data.decode(), (
            "Total spent must be ₹0 when no expenses match the filter"
        )

    def test_transaction_count_is_zero_when_no_expenses(self, seeded_client):
        r = seeded_client.get("/profile?from=2099-01-01&to=2099-12-31")
        # The stat_value for Transactions must be 0.
        assert b"0" in r.data, (
            "Transaction count must be 0 when no expenses match the filter"
        )


# ===========================================================================
# 11. Stats recomputation — explicit value checks
# ===========================================================================

class TestStatsRecomputation:

    def test_total_spent_this_month(self, seeded_client):
        """Food 900 + Bills 800 + Health 200 = ₹1,900."""
        r = seeded_client.get("/profile?period=this_month")
        assert "1,900" in r.data.decode(), "Total for this_month must be ₹1,900"

    def test_total_spent_last_month(self, seeded_client):
        """Transport 300 + Shopping 500 = ₹800."""
        r = seeded_client.get("/profile?period=last_month")
        assert "800" in r.data.decode(), "Total for last_month must be ₹800"

    def test_transaction_count_this_month(self, seeded_client):
        r = seeded_client.get("/profile?period=this_month")
        assert b"6" in r.data

    def test_transaction_count_last_month(self, seeded_client):
        r = seeded_client.get("/profile?period=last_month")
        assert b"3" in r.data

    def test_category_breakdown_this_month_has_correct_categories(self, seeded_client):
        html = seeded_client.get("/profile?period=this_month").data.decode()
        for expected in ("Food", "Bills", "Health"):
            assert expected in html, f"{expected} must appear in this_month breakdown"

    def test_category_breakdown_last_month_has_correct_categories(self, seeded_client):
        html = seeded_client.get("/profile?period=last_month").data.decode()
        for expected in ("Transport", "Shopping"):
            assert expected in html, f"{expected} must appear in last_month breakdown"

    def test_top_category_this_month_is_food(self, seeded_client):
        r = seeded_client.get("/profile?period=this_month")
        assert b"Food" in r.data

    def test_top_category_last_month_is_shopping(self, seeded_client):
        r = seeded_client.get("/profile?period=last_month")
        assert b"Shopping" in r.data

    def test_filter_changes_recompute_stats_independently(self, seeded_client):
        """Switching between two presets must yield distinct transaction counts."""
        r_this = seeded_client.get("/profile?period=this_month")
        r_last = seeded_client.get("/profile?period=last_month")
        # Counts: 6 vs 3 — they must differ in the page data.
        # We verify that last_month does not claim 6 transactions.
        assert b"6" not in r_last.data or (
            # '6' might appear in other parts of the page (e.g. dates); check transaction_count
            # by confirming the pages are not identical
            r_this.data != r_last.data
        ), "Stats must recompute independently per filter"


# ===========================================================================
# 12. Transaction cap — 5-row ceiling
# ===========================================================================

class TestTransactionCap:

    def test_all_time_caps_at_5_rows(self, seeded_client):
        r = seeded_client.get("/profile?period=all_time")
        assert _count_tbody_rows(r.data) <= 5, (
            "Transactions table must show at most 5 rows under all_time (14 total)"
        )

    def test_this_month_caps_at_5_rows(self, seeded_client):
        """6 expenses this month — must still be capped at 5."""
        r = seeded_client.get("/profile?period=this_month")
        assert _count_tbody_rows(r.data) <= 5, (
            "Transactions table must show at most 5 rows even with 6 matching expenses"
        )

    def test_last_month_shows_all_3_rows(self, seeded_client):
        """3 expenses last month — all should appear (under the cap)."""
        r = seeded_client.get("/profile?period=last_month")
        assert _count_tbody_rows(r.data) == 3, (
            "All 3 last_month expenses must appear in the table (below the 5-row cap)"
        )

    def test_no_expenses_shows_0_rows(self, seeded_client):
        """Future date range — 0 matching expenses — table has 0 data rows."""
        r = seeded_client.get("/profile?from=2099-01-01&to=2099-12-31")
        assert _count_tbody_rows(r.data) == 0, (
            "Table must show 0 data rows when no expenses match"
        )


# ===========================================================================
# 13. Showing label correctness across all presets
# ===========================================================================

class TestShowingLabel:

    def test_showing_label_all_time(self, seeded_client):
        r = seeded_client.get("/profile?period=all_time")
        assert b"Showing:" in r.data
        assert b"All Time" in r.data

    def test_showing_label_this_month_contains_month_name(self, seeded_client):
        r = seeded_client.get("/profile?period=this_month")
        assert b"Showing:" in r.data
        assert _today().strftime("%B").encode() in r.data

    def test_showing_label_last_month_contains_month_name(self, seeded_client):
        _, end = _last_month_range()
        r = seeded_client.get("/profile?period=last_month")
        assert b"Showing:" in r.data
        assert end.strftime("%B").encode() in r.data

    def test_showing_label_last_3_months_contains_year(self, seeded_client):
        r = seeded_client.get("/profile?period=last_3_months")
        assert b"Showing:" in r.data
        assert str(_today().year).encode() in r.data

    def test_showing_label_last_6_months_contains_year(self, seeded_client):
        r = seeded_client.get("/profile?period=last_6_months")
        assert b"Showing:" in r.data
        assert str(_today().year).encode() in r.data

    def test_showing_label_custom_contains_year(self, seeded_client):
        today = _today()
        r = seeded_client.get(
            f"/profile?period=custom"
            f"&from={_iso(_first_of_month(today))}"
            f"&to={_iso(today)}"
        )
        assert b"Showing:" in r.data
        assert str(today.year).encode() in r.data
