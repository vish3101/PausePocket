# Spec: Expense List

## Overview
This feature replaces the `/expenses` stub with a fully functional expense dashboard that reads real data from the database. It is the first route in the app to execute live SQL queries against the `expenses` table, displaying the logged-in user's transactions in a sortable table alongside summary stats (total spent, transaction count, top category) and a per-category breakdown. Step 5 is the primary day-to-day screen users will land on after login; all subsequent expense features (add, edit, delete) link back to it.

## Depends on
- Step 1: Database setup (`expenses` table and `get_db()` must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login / Logout (session must be established; route must be protected)
- Step 4: Profile page (establishes the authenticated layout pattern and CSS components to reuse)

## Routes
- `GET /expenses` — render the expense dashboard with live DB data — logged-in only (redirect to `/login` if not authenticated)

## Database changes
No database changes. The existing `expenses` table schema (`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`) is sufficient.

## Templates
- **Create:** `templates/expenses.html` — expense dashboard extending `base.html`; contains:
  1. **Page header** — title ("My Expenses") and an "Add Expense" button (links to `/expenses/add`)
  2. **Summary stats row** — total spent (₹), number of transactions, top category (computed from DB)
  3. **Category breakdown** — per-category totals as a simple list or progress-bar rows
  4. **Expense table** — columns: Date, Description, Category, Amount; rows ordered by date descending; each row has placeholder Edit and Delete links (`/expenses/<id>/edit`, `/expenses/<id>/delete`)
  5. **Empty state** — a friendly message when the user has no expenses yet

## Files to change
- `app.py` — replace the `/expenses` stub with a real view function that:
  - Redirects unauthenticated users to `/login`
  - Queries all expenses for `session["user_id"]` ordered by `date DESC`
  - Computes summary stats in Python: total amount, count, top category
  - Computes per-category totals in Python from the fetched rows
  - Passes `expenses`, `stats`, and `categories` context to `expenses.html`

## Files to create
- `templates/expenses.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- All summary stats and category totals must be computed from the real DB rows in `app.py`, not hardcoded
- Amounts must be formatted as `₹X,XXX.XX` (Indian locale formatting) in the Python view before passing to the template — do not format in Jinja
- Category badges must use a CSS class, not inline colour styles (reuse the pattern from `profile.html`)
- Edit and Delete links must be present in the table but will return plain-text stubs — do not implement those handlers in this step
- Do not add pagination or filtering — display all expenses for the user

## Definition of done
- [ ] Visiting `/expenses` without being logged in redirects to `/login`
- [ ] Visiting `/expenses` while logged in returns HTTP 200
- [ ] The page displays a summary row with total spent, transaction count, and top category derived from real DB data
- [ ] The page displays a table listing all expenses for the logged-in user, ordered newest first
- [ ] Each table row shows the correct date, description, category, and amount from the DB
- [ ] The page displays a per-category breakdown computed from the user's actual expenses
- [ ] When a user has no expenses, a friendly empty-state message is shown instead of an empty table
- [ ] The "Add Expense" button links to `/expenses/add`
- [ ] Each row contains an Edit link to `/expenses/<id>/edit` and a Delete link to `/expenses/<id>/delete`
- [ ] The navbar shows the logged-in state (username + logout link)
- [ ] No hex colour values appear in `expenses.html` — only CSS variables
- [ ] The seeded demo user's 8 expenses (from `seed_db()`) are visible when logged in as `demo@spendly.com`
