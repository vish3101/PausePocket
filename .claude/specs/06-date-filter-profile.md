# Spec: Date Filter for Profile Page

## Overview
This feature adds a date-range filter to the `/profile` page so users can narrow the displayed stats and transaction history to a specific period. Currently the profile page always computes totals across all-time expenses. With this filter, users can select a preset period (This Month, Last Month, Last 3 Months, Last 6 Months, All Time) or supply a custom `from` / `to` date pair via query-string parameters. The route re-queries the database using the selected range and recomputes stats, category breakdown, and recent transactions from only the matching rows. No new routes are needed — all filtering happens through GET query parameters on the existing `/profile` route.

## Depends on
- Step 1: Database setup (`expenses` table and `get_db()` must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login / Logout (session must be established; `/profile` must be protected)
- Step 4: Profile page (`profile.html` template and the `/profile` view function must already exist)
- Step 5: Expense list (establishes the live-query pattern this feature extends)

## Routes
No new routes. The existing `GET /profile` route is extended to accept optional query parameters:
- `?period=this_month` | `last_month` | `last_3_months` | `last_6_months` | `all_time` (default: `all_time`)
- `?from=YYYY-MM-DD&to=YYYY-MM-DD` — custom range; takes precedence over `period` when both are present

## Database changes
No database changes. The existing `expenses` table schema is sufficient; date filtering is applied in the SQL `WHERE` clause using parameterised queries.

## Templates
- **Modify:** `templates/profile.html` — add a filter bar above the stats row containing:
  1. **Preset buttons** — five buttons (This Month, Last Month, Last 3 Months, Last 6 Months, All Time); the active preset is visually highlighted
  2. **Custom date inputs** — two `<input type="date">` fields (From / To) with a small "Apply" submit button
  3. Both controls submit as a plain HTML `<form method="GET" action="/profile">` — no JavaScript required for basic operation
  4. The "active period" label (e.g. "Showing: April 2026") is displayed next to the filter bar to confirm what range is applied

## Files to change
- `app.py` — update the `/profile` view function to:
  - Read `period`, `from`, and `to` from `request.args`
  - Compute `date_from` and `date_to` as ISO strings (`YYYY-MM-DD`) based on the active filter
  - Pass `date_from` and `date_to` as SQL parameters in the `expenses` query (`WHERE user_id = ? AND date BETWEEN ? AND ?`)
  - Recompute `total`, `category_totals`, `top_category`, and `transactions` (capped at 5) from the filtered rows
  - Pass `active_period`, `date_from`, `date_to`, and `period` back to the template so the UI can reflect the current selection

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never string-format SQL or inject date values directly into query strings
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- Date arithmetic must use Python's `datetime` / `date` stdlib only — no third-party date libraries
- `date_from` and `date_to` must always be valid ISO date strings before being passed to SQL; if custom inputs are malformed or missing, fall back to `all_time` silently
- The filter form must use `method="GET"` so the selected range is bookmarkable and shareable
- The active preset button must be indicated via a CSS class (e.g. `btn-primary` vs `btn-ghost`) — not inline styles
- Do not add JavaScript to the filter UI in this step; plain HTML form submission is sufficient
- The `transactions` list passed to the template remains capped at 5 rows (most recent within the filtered range)

## Definition of done
- [ ] Visiting `/profile` without query params shows all-time data (same behaviour as before this step)
- [ ] Clicking "This Month" filters stats and transactions to the current calendar month
- [ ] Clicking "Last Month" filters to the previous calendar month
- [ ] Clicking "Last 3 Months" filters to the 90-day window ending today
- [ ] Clicking "Last 6 Months" filters to the 180-day window ending today
- [ ] The active preset button is visually distinct from the inactive ones
- [ ] Entering a custom From / To date and clicking Apply filters the page to that exact range
- [ ] A malformed or missing custom date falls back to all-time without a 500 error
- [ ] The "Showing: …" label correctly reflects the active date range
- [ ] All stats (total spent, transaction count, top category) update to reflect only expenses in the selected range
- [ ] The category breakdown updates to reflect only expenses in the selected range
- [ ] The transaction history table shows at most 5 rows from within the selected range
- [ ] No hex colour values appear in `profile.html` — only CSS variables
- [ ] The navbar shows the logged-in state (username + logout link)
