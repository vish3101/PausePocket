# Spec: Registration

## Overview
This step wires up the `POST /register` handler so new users can create an account. The registration form already exists in `register.html` and posts `name`, `email`, and `password` to `/register`. The handler validates the input, hashes the password with Werkzeug, inserts the user into the `users` table, and redirects to the login page on success. On failure (duplicate email, short password, missing fields) it re-renders the form with an inline error message via the `{{ error }}` variable the template already supports. A `secret_key` must also be set on the Flask app so the session is usable in Step 3.

## Depends on
- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table must exist)

## Routes
- `POST /register` — validate form data, insert user, redirect to `/login` — public
- `GET /register` — already exists; no change needed beyond accepting both methods on one route

## Database changes
No database changes. The `users` table (id, name, email, password_hash, created_at) is already created by `init_db()` in Step 1.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — preserve `name` and `email` field values on POST error so the user does not have to retype them (pass `name` and `email` back via `render_template`)

## Files to change
- `app.py` — add `app.secret_key`, update `/register` route to handle `GET` and `POST`, import `request` and `redirect` from Flask, import `generate_password_hash` from `werkzeug.security`

## Files to create
None

## New dependencies
No new dependencies. `werkzeug.security` is already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`; never store plain text
- Use CSS variables — never hardcode hex values in any template or stylesheet
- All templates extend `base.html`
- `secret_key` must be set before any session or redirect use — use a hard-coded dev string for now (e.g. `"dev-secret-change-in-prod"`); do not use `os.urandom` as it regenerates on every restart during development
- Catch `sqlite3.IntegrityError` to detect duplicate email — do not pre-query for existence (race condition)
- Minimum password length: 8 characters — validate server-side, not just via HTML `minlength`
- On success redirect to `url_for('login')` — do not auto-login (that is Step 3)
- Use `methods=["GET", "POST"]` on the single `/register` route — do not create a separate route for POST

## Definition of done
- [ ] Visiting `/register` renders the form (GET still works)
- [ ] Submitting the form with valid data inserts a new row in `users` and redirects to `/login`
- [ ] The inserted `password_hash` is a Werkzeug bcrypt hash, not plain text
- [ ] Submitting with an already-registered email re-renders the form with an error message (no crash)
- [ ] Submitting with a password shorter than 8 characters re-renders the form with an error message
- [ ] Submitting with any field blank re-renders the form with an error message
- [ ] After an error, `name` and `email` fields are pre-filled with the values the user typed
- [ ] App starts without errors after changes to `app.py`
