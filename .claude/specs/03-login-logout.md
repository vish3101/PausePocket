# Spec: Login and Logout

## Overview
This step wires up session-based authentication so registered users can sign in and sign out. The `POST /login` handler reads the submitted email and password, looks up the user in the `users` table, verifies the password with Werkzeug's `check_password_hash`, and stores the user's `id` and `name` in Flask's server-side session on success. On failure it re-renders `login.html` with an inline error. The `GET /logout` route clears the session and redirects to the landing page. After this step, `session["user_id"]` is the canonical way for later steps to identify the logged-in user.

## Depends on
- Step 1 — Database setup (`get_db()`, `users` table must exist)
- Step 2 — Registration (`users` rows must be insertable so there is something to log in with)

## Routes
- `POST /login` — validate credentials, set session, redirect to `/expenses` — public
- `GET /login` — render sign-in form — public (already exists; extend to accept both methods)
- `GET /logout` — clear session, redirect to `/` — public (stub already exists)

## Database changes
No database changes. The `users` table already has `id`, `email`, and `password_hash`, which are the only columns needed for login.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — already renders `{{ error }}`; no structural change needed. Pass `email` back on POST failure so the field stays pre-filled (mirror the register pattern).

## Files to change
- `app.py`
  - Add `session` to the Flask import
  - Add `check_password_hash` to the `werkzeug.security` import
  - Update `/login` route: accept `GET` and `POST`, handle POST logic
  - Update `/logout` route: clear session and redirect to landing

## Files to create
None

## New dependencies
No new dependencies. `werkzeug.security` and Flask sessions are already available.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plain text
- Use CSS variables — never hardcode hex values in any template or stylesheet
- All templates extend `base.html`
- Store only `user_id` (int) and `user_name` (str) in the session — never store the password hash or full row
- Use a single generic error message for both "email not found" and "wrong password" — do not reveal which field was wrong
- On success redirect to `url_for('expenses')` — that route is a stub for now; it will be implemented in Step 5
- On POST failure re-render `login.html` passing `error=` and `email=` so the email field stays filled
- Use `methods=["GET", "POST"]` on the single `/login` route — do not create a separate route for POST
- Do not add a `@login_required` decorator yet — that belongs in Step 4/5 once protected routes are implemented

## Definition of done
- [ ] Visiting `/login` renders the sign-in form (GET still works)
- [ ] Submitting a valid email + password sets `session["user_id"]` and redirects to `/expenses`
- [ ] Submitting a valid email + wrong password re-renders the form with a generic error (no crash, no stack trace)
- [ ] Submitting an email that does not exist re-renders the form with the same generic error
- [ ] After a login failure, the email field is pre-filled with the value the user typed
- [ ] Visiting `/logout` clears the session and redirects to `/`
- [ ] After logout, `session.get("user_id")` returns `None`
- [ ] App starts without errors after all changes to `app.py`
