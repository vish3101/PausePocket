# Spec: Profile

## Overview
This step replaces the `/profile` stub with a real page that shows the logged-in user's account details — their name, email, and the date they joined. The page is login-protected: any visitor without an active session is redirected to `/login`. It is the first genuinely protected route in the app and establishes the guard pattern (`session.get("user_id")`) that all subsequent logged-in routes will reuse.

## Depends on
- Step 1 — Database setup (`get_db()`, `users` table must exist)
- Step 3 — Login and Logout (session must be set before this page can be reached)

## Routes
- `GET /profile` — render the user's profile page — logged-in only (redirect to `/login` if no session)

## Database changes
No database changes. The `users` table already has `id`, `name`, `email`, and `created_at`, which are all the columns needed.

## Templates
- **Create:**
  - `templates/profile.html` — profile page showing name, email, and member-since date
- **Modify:**
  - `templates/base.html` — add a "Profile" nav link visible only when `session.user_id` is set (and update any existing nav links as needed)

## Files to change
- `app.py` — replace the `/profile` stub with a real handler that guards with session, queries the user row, and passes data to the template
- `templates/base.html` — add session-aware nav link to profile and logout

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Passwords hashed with werkzeug (not applicable here, but do not expose `password_hash` to the template under any variable name)
- Use CSS variables — never hardcode hex values in any template or stylesheet
- All templates extend `base.html`
- Guard pattern: `if not session.get("user_id"): return redirect(url_for("login"))` — use this exact check at the top of every protected route
- Query the DB by `user_id` from the session — do not trust any URL parameter or form field for identity
- Pass only `name`, `email`, and `created_at` to the template — never pass the full row or `password_hash`
- Format `created_at` for display in the route (e.g. `"April 2, 2026"`) rather than in the template
- Reuse existing CSS classes from `style.css` for the page layout — do not write new component styles unless unavoidable

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] After logging in, visiting `/profile` renders the profile page (no crash, no plain text)
- [ ] The page displays the logged-in user's name, email, and join date
- [ ] The join date is human-readable (not a raw SQLite datetime string)
- [ ] Visiting `/logout` then `/profile` redirects to `/login` again (session correctly cleared)
- [ ] The nav in `base.html` shows a profile/logout link when logged in and hides it when logged out
- [ ] App starts without errors after all changes
