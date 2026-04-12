from functools import wraps
from flask import session, redirect, url_for, flash

"""
Shared authentication decorators for route protection.
Used across all blueprints to enforce login requirements
instead of repeating session checks in every route.
"""


def require_user_login(f):
    """
    Decorator that redirects to login page if no user session exists.
    Apply to any route that requires a logged-in end user.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.")
            return redirect(url_for('auth_bp.login_page'))
        return f(*args, **kwargs)
    return decorated_function


def require_client_login(f):
    """
    Decorator that redirects to client login if no client session exists.
    Apply to any route that requires a logged in client/organisation.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'client_id' not in session:
            flash("Please log in to access this page.")
            return redirect(url_for('client_bp.client_login'))
        return f(*args, **kwargs)
    return decorated_function


def require_audit_access(f):
    """
    Decorator that allows access if either a client or auditor is logged in.
    Used for the audit dashboard which both roles can access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'auditor_id' not in session and 'client_id' not in session:
            flash("Please log in to access the audit dashboard.")
            return redirect(url_for('admin_bp.auditor_login'))
        return f(*args, **kwargs)
    return decorated_function
