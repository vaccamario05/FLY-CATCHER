"""
Module: web/auth.py
Sprint: 2
Purpose: Authentication and RBAC for ADS-B Secure dashboard.

Roles:
  operator — view dashboard and traces
  analyst  — view + audit logs + export

Passwords stored as werkzeug PBKDF2-SHA256 hashes.
Session timeout: 30 minutes inactivity.
"""

import functools
import logging
import os
import secrets
import time
from typing import Optional

from flask import Blueprint, redirect, render_template_string, request, session, url_for, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", "1800"))  # 30 min

auth_bp = Blueprint("auth", __name__)

# ---------------------------------------------------------------------------
# In-memory user store (Sprint 2 — no DB needed for prototype)
# Bootstrap users from env. No hardcoded fallback (CWE-259): if a password
# env var is unset, a random one-time password is generated and logged once
# at startup — never persisted, never a static known value.
# ---------------------------------------------------------------------------

def _bootstrap_password(env_var: str, role: str) -> str:
    password = os.environ.get(env_var)
    if password:
        return password
    password = secrets.token_urlsafe(16)
    logger.warning(
        "%s not set — generated one-time password for role=%s: %s",
        env_var, role, password,
    )
    return password


_USERS: dict[str, dict] = {
    "operator": {
        "password_hash": generate_password_hash(
            _bootstrap_password("OPERATOR_PASSWORD", "operator")
        ),
        "role": "operator",
    },
    "supervisor": {
        "password_hash": generate_password_hash(
            _bootstrap_password("SUPERVISOR_PASSWORD", "supervisor")
        ),
        "role": "supervisor",
    },
    "analyst": {
        "password_hash": generate_password_hash(
            _bootstrap_password("ANALYST_PASSWORD", "analyst")
        ),
        "role": "analyst",
    },
}

_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ADS-B Secure — Login</title>
  <style>
    body { font-family: monospace; background: #0a0a0a; color: #00ff41;
           display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
    .box { border: 1px solid #00ff41; padding: 2rem; min-width: 300px; }
    h2 { margin-top:0; }
    input { background:#111; color:#00ff41; border:1px solid #333;
            padding:.4rem .6rem; width:100%; box-sizing:border-box; margin:.3rem 0 .8rem; }
    button { background:#00ff41; color:#000; border:none; padding:.5rem 1.2rem;
             cursor:pointer; font-weight:bold; }
    .err { color:#ff4444; margin-bottom:.8rem; }
  </style>
</head>
<body>
  <div class="box">
    <h2>ADS-B Secure</h2>
    {% if error %}<p class="err">{{ error }}</p>{% endif %}
    <form method="post">
      <label>Username</label>
      <input name="username" autocomplete="username" required>
      <label>Password</label>
      <input name="password" type="password" autocomplete="current-password" required>
      <button type="submit">Login</button>
    </form>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _session_valid() -> bool:
    if "username" not in session:
        return False
    last = session.get("last_active", 0)
    if time.time() - last > SESSION_TIMEOUT:
        session.clear()
        return False
    session["last_active"] = time.time()
    return True


def current_user() -> Optional[dict]:
    if not _session_valid():
        return None
    username = session.get("username")
    return _USERS.get(username)


def current_role() -> Optional[str]:
    u = current_user()
    return u["role"] if u else None


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def require_auth(f):
    """Redirect to login if not authenticated."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not _session_valid():
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def require_role(role: str):
    """Return 403 if authenticated user lacks required role."""
    _ROLE_HIERARCHY = {"operator": 0, "supervisor": 1, "analyst": 2}

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not _session_valid():
                if request.path.startswith("/api/"):
                    return jsonify({"error": "unauthorized"}), 401
                return redirect(url_for("auth.login"))
            user_role = current_role()
            if _ROLE_HIERARCHY.get(user_role, -1) < _ROLE_HIERARCHY.get(role, 99):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "forbidden", "required": role}), 403
                return "403 Forbidden", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.get("/login")
def login():
    if _session_valid():
        return redirect(url_for("dashboard"))
    return render_template_string(_LOGIN_HTML, error=None)


@auth_bp.post("/login")
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    from flask import current_app
    flog = getattr(current_app, "forensic_logger", None)

    user = _USERS.get(username)
    if user and check_password_hash(user["password_hash"], password):
        session.clear()
        session["username"] = username
        session["role"] = user["role"]
        session["last_active"] = time.time()
        logger.info("Login success: %s (role=%s)", username, user["role"])
        if flog:
            from security.forensic_logger import SecurityEvent, EventType, Severity
            flog.log(SecurityEvent(
                event_type=EventType.LOGIN_SUCCESS,
                severity=Severity.LOW,
                details={"username": username, "role": user["role"]},
            ))
        return redirect(url_for("dashboard"))

    logger.warning("Login failed: username=%r", username)
    if flog:
        from security.forensic_logger import SecurityEvent, EventType, Severity
        flog.log(SecurityEvent(
            event_type=EventType.LOGIN_FAILED,
            severity=Severity.MEDIUM,
            details={"username": username},
        ))
    return render_template_string(_LOGIN_HTML, error="Invalid credentials"), 401


@auth_bp.get("/logout")
def logout():
    username = session.get("username", "?")
    session.clear()
    logger.info("Logout: %s", username)
    return redirect(url_for("auth.login"))
