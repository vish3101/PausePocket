# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pause Pocket (branded "Spendly" on the landing page) is a personal expense tracking web app targeting Indian users (currency: ₹). It is a learning project built with Flask and SQLite. Users will be able to register, log in, and manage personal expenses. The app is in early development — the database, authentication, and expense features are not yet implemented.

## Architecture

```
expense-tracker/
├── app.py                  # Single-file Flask app — all routes live here
├── database/
│   └── db.py               # SQLite helpers (stub — not yet implemented)
├── templates/
│   ├── base.html           # Root template; all pages extend this
│   ├── landing.html        # Public landing page (hero, features, modal)
│   ├── login.html          # Sign-in form
│   ├── register.html       # Registration form
│   ├── terms.html          # Terms and conditions
│   └── privacy.html        # Privacy policy
└── static/
    ├── css/
    │   ├── style.css       # Global design system (CSS variables, components)
    │   └── landing.css     # Landing-page overrides (hero, dashboard mockup)
    └── js/
        └── main.js         # Currently empty; landing modal is inline in landing.html
```

All routes are in `app.py` — no blueprints. Templates inherit from `base.html` using blocks: `{% block title %}`, `{% block head %}`, `{% block content %}`, `{% block scripts %}`.

`database/db.py` will expose three helpers once implemented: `get_db()`, `init_db()`, `seed_db()`.

## Code Style

- Use Python type hints on all new functions.
- Use `render_template()` for all routes that return HTML — no raw string responses in final code.
- Keep all route logic in `app.py` for now; extract to service functions inside `database/` only when logic grows complex.
- All JavaScript must be vanilla — no libraries or frameworks. Page-specific scripts go in `{% block scripts %}` at the bottom of the template.
- Use existing CSS custom properties from `style.css` `:root` — do not hardcode colour or font values. Key tokens: `--ink`, `--paper`, `--accent`, `--accent-2`, `--danger`, `--font-display`, `--font-body`.
- Reuse button classes: `.btn-primary`, `.btn-ghost`, `.btn-submit`.

## Tech Constraints

| Layer | Choice | Avoid |
|---|---|---|
| Backend | Flask 3.1.3 | Django, FastAPI, or any other framework |
| Database | SQLite via stdlib `sqlite3` | SQLAlchemy, ORMs, or external databases |
| Templating | Jinja2 (built into Flask) | Client-side rendering frameworks |
| Frontend JS | Vanilla JS only | jQuery, React, Vue, Alpine, HTMX, or any CDN library |
| CSS | Plain CSS with custom properties | Tailwind, Bootstrap, or any CSS framework |
| Auth | Flask session (stdlib) | Flask-Login, JWT, or third-party auth libraries |

Do not add any packages beyond what is already in `requirements.txt` without confirming with the user first.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server (http://localhost:5001)
python app.py

# Run tests
pytest

# Run a single test file
pytest tests/test_routes.py
```

## Development Roadmap

Features are built in a fixed step order. Do not skip steps or implement a later step before its dependencies exist.

| Step | Feature | Route(s) | Status |
|------|---------|----------|--------|
| 1 | Database setup | — | Not started |
| 2 | Register (POST handler + DB write) | `POST /register` | Not started |
| 3 | Login / Logout (session) | `POST /login`, `GET /logout` | Not started |
| 4 | Profile page | `GET /profile` | Not started |
| 5 | Expense list (dashboard) | `GET /expenses` | Not started |
| 6 | Expense detail view | `GET /expenses/<int:id>` | Not started |
| 7 | Add expense | `GET/POST /expenses/add` | Not started |
| 8 | Edit expense | `GET/POST /expenses/<int:id>/edit` | Not started |
| 9 | Delete expense | `GET /expenses/<int:id>/delete` | Not started |

Routes for Steps 3–9 already exist in `app.py` as stubs returning plain text.

## Warnings & Things to Avoid

- **Do not commit `expense_tracker.db`** — it is gitignored. Never create or manipulate the DB file directly; always go through `db.py` helpers.
- **Do not implement `database/db.py` partially** — complete `get_db()`, `init_db()`, and `seed_db()` together in Step 1 before touching any other feature.
- **Do not generate user IDs or expense IDs manually** — SQLite `INTEGER PRIMARY KEY` auto-increments; let the DB assign them.
- **Do not store passwords in plain text** — use `werkzeug.security.generate_password_hash` / `check_password_hash` (Werkzeug is already installed).
- **Do not change the branding inconsistency** (Pause Pocket vs. Spendly) without explicit instruction — it is a known issue.
- **Do not move modal JS out of `landing.html`** into `main.js` unless asked — the inline script handles iframe `src` clearing on close, which is intentional.
- **Do not add new pip packages** without user approval — the stack is intentionally minimal for a learning project.
