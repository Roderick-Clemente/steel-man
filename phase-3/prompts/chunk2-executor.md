# Executor prompt — Phase 3, Chunk 2: route + template

You are the executor for an adversarial-sprint Phase 3 chunk. Your job is to
implement the `GET /profile` route and template so the locked test passes,
without touching any test file.

## Locked test

The test file `test/test_profile_route.py` is locked and must not be modified.
It asserts: auth-required redirect, no data leak on redirect, all four fields
rendered for authenticated user, no internal columns in body, stale-session
redirect (A5), and DB-over-session source-of-truth (A3).

## What to implement

### 1. `api/profile.py` (new file)

Create `api/profile.py` with a `handle_profile()` function:

```python
from flask import render_template, session, redirect, url_for
from models import get_user_profile


def handle_profile():
    """Handle profile page — session-scoped, read-only, no URL parameter."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    profile = get_user_profile(session["user_id"])

    if profile is None:
        return redirect(url_for("login"))

    return render_template("profile.html", profile=profile)
```

Key properties:
- **No `?id=` parameter** (deliberate contrast with `api/accounts.py`).
- **Data from DB via `get_user_profile`**, not from session copies.
- **None → redirect to login** (fail-closed, no 500).
- **Single context variable `profile`** passed to the template.

### 2. `templates/profile.html` (new file)

Create a standalone HTML template (no `{% extends %}` — the pilot has no
`base.html`). Mirror the navbar/`banking.css` structure of
`templates/account_detail.html`. Reference ONLY:
- `{{ profile.username }}`
- `{{ profile.email }}`
- `{{ profile.full_name }}`
- `{{ profile.address }}`

Do NOT reference `profile.id`, `profile.created_at`, or any other key.

Example structure:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Profile - Quantum Bank</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/banking.css') }}">
</head>
<body>
    <nav class="navbar">
        <div class="navbar-container">
            <a href="/dashboard" class="navbar-brand">Quantum Bank</a>
            <ul class="navbar-nav">
                <li><a href="/dashboard" class="nav-link">Dashboard</a></li>
                <li><a href="/transactions" class="nav-link">Transactions</a></li>
                <li><a href="/logout" class="nav-link">Logout</a></li>
            </ul>
        </div>
    </nav>
    <div class="container">
        <h1>Profile</h1>
        <div class="account-card" style="cursor: default;">
            <div style="margin-bottom: 1rem;">
                <strong>Username:</strong> {{ profile.username }}
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Email:</strong> {{ profile.email }}
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Full Name:</strong> {{ profile.full_name }}
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Address:</strong> {{ profile.address }}
            </div>
        </div>
    </div>
</body>
</html>
```

### 3. `app.py` (edit — one import + one route)

Add the import alongside the existing api imports (near line 32-33):
```python
from api.profile import handle_profile
```

Add the route in the banking block (after the `account` route, ~line 203):
```python
@app.route("/profile")
def profile():
    return handle_profile()
```

Do NOT reorder existing routes. Do NOT add a nav link (out of scope per plan §7).

## Constraints

- You may edit ONLY: `api/profile.py` (new), `templates/profile.html` (new),
  `app.py` (one import + one route).
- You may NOT edit any test file.
- You may NOT edit `models.py` (chunk 1's territory).
- You may run `pytest test/test_profile_route.py -v` to confirm GREEN.
- You may run `pytest -q` to confirm no regressions.
- If blocked, report and stop.

## Output

Create `api/profile.py`, create `templates/profile.html`, edit `app.py`, and
stop.
