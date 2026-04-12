from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from application.services.authentication import register_user, authenticate_user, validate_password
from werkzeug.security import check_password_hash
from application.services.decorators import require_user_login
from data.user_database import (
    find_by_username, find_by_id, get_user_data, delete_user,
    delete_user_data_only, update_last_login, create_user_profile
)
from data.db_connection import get_db
from application.services.audit_service import (
    audit_log, log_login_success, log_login_failed, log_logout,
    log_data_create, log_data_delete, log_data_update, log_data_export
)
from data.submission_database import (
    get_user_submissions, withdraw_consent, reinstate_consent,
    delete_single_submission, get_user_dashboard_stats
)
from data.dsr_database import get_dsrs_for_user
from application.services.otp_service import (
    generate_otp, store_otp, verify_otp,
    generate_reset_token, store_reset_token, verify_reset_token, invalidate_reset_token
)
from application.services.email_service import send_otp_email, send_password_reset_email
from application.services.dsr_service import log_dsr
from werkzeug.security import generate_password_hash
from application.extensions import limiter
import os
import csv
import io
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
USERNAME_RE = re.compile(r'^[a-zA-Z0-9_.\-]+$')


def _valid_email(email):
    """Return True if email matches a basic format check."""
    return bool(EMAIL_RE.match(email))


def _valid_username(username):
    """Return (is_valid, error_message). Checks length and allowed characters."""
    if not username or len(username.strip()) == 0:
        return False, "Username is required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 50:
        return False, "Username must be 50 characters or fewer."
    if not USERNAME_RE.match(username):
        return False, "Username may only contain letters, numbers, underscores, hyphens, and dots."
    return True, ""


def _safe_referrer_redirect(fallback):
    """Redirect to request.referrer only if it belongs to the same host, preventing open redirects."""
    ref = request.referrer
    if ref:
        ref_parsed = urlparse(ref)
        host_parsed = urlparse(request.host_url)
        if ref_parsed.netloc == host_parsed.netloc and ref_parsed.scheme == host_parsed.scheme:
            return redirect(ref)
    return redirect(fallback)


# auth_bp is an object of Blueprint that stores its name (auth_bp)
# The module where it is definined is inside of __name__
# And all routes that belong to it

auth_bp = Blueprint('auth_bp', __name__)
pages_bp = Blueprint('pages_bp', __name__)


def _get_user_email(user_id):
    """Decrypt and return the users email address, or None if not found."""
    key = os.getenv("APP_ENC_KEY")
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT pgp_sym_decrypt(email_enc::bytea, %s) FROM users WHERE id = %s;
        """, (key, user_id))
        row = cur.fetchone()
    return row[0] if row else None

# Below are all the routes and actions that are assigned to auth_bp
# These include displaying pages to users and allowing them to login and register


@auth_bp.route('/')
def login_page():
    return render_template('landing.html')


@auth_bp.route('/register')
def register_page():
    return render_template('Register.html')


@auth_bp.route('/register_user', methods=['POST'])
@limiter.limit("3 per minute")
def register():
    username = request.form['username'].strip()
    password = request.form['password']
    age = request.form['age']
    address = request.form['address']
    email = request.form.get('email', '').strip()

    # Validate username format and length
    uname_ok, uname_err = _valid_username(username)
    if not uname_ok:
        flash(uname_err, "danger")
        return redirect(url_for('auth_bp.register_page'))

    if not email:
        flash("Email address is required.", "danger")
        return redirect(url_for('auth_bp.register_page'))

    if not _valid_email(email):
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for('auth_bp.register_page'))

    # Validate password strength
    valid, msg = validate_password(password)
    if not valid:
        flash(msg, "danger")
        return redirect(url_for('auth_bp.register_page'))

    # Validate age, must be 18+ to use the system
    try:
        age_int = int(age)
        if age_int < 18:
            flash("You must be at least 18 years old to use this system.", "danger")
            return redirect(url_for('auth_bp.register_page'))
        if age_int > 120:
            flash("Please enter a valid age.", "danger")
            return redirect(url_for('auth_bp.register_page'))
        age = age_int
    except (ValueError, TypeError):
        flash("Please enter a valid age.", "danger")
        return redirect(url_for('auth_bp.register_page'))

    # Check to see if username already exists
    existing_user = find_by_username(username)
    if existing_user:
        flash("Username already exists. Please choose another.", "danger")
        return redirect(url_for('auth_bp.register_page'))

    # The register_user function inserts a user into the database
    register_user(username, password)
    session['username'] = username
    # make a second call to get the id. This is needed for entries
    # to be accteped into the database throught the questionnaire
    user = find_by_username(username)
    if not user:
        return redirect(url_for('auth_bp.login_page'))

    session['user_id'] = user[0]
    user_id = user[0]

    # Create the user profile (encrypted email, base submission, PII, demographics)
    create_user_profile(user_id, username, email, address, age)

    # Log new user registration
    log_data_create('users', user_id, {'action': 'registration'})
    log_login_success(user_id, 'user')

    # Set last_activity for session timeout tracking
    session.permanent = True
    session['last_activity'] = time.time()

    # Flag for first time user tutorial
    session['first_login'] = True

    return redirect(url_for('home_bp.homepage'))


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    username = request.form['username']
    password = request.form['password']
    # Make a call to the authenticate_user function and the user_id
    # of the linked account is stored in user_id
    user_id = authenticate_user(username, password)
    if user_id:
        # Fetch the users encrypted email for OTP delivery
        user_email = _get_user_email(user_id)

        if not user_email:
            # No email on record, skip 2FA and log them straight in (legacy accounts)
            session['user_id'] = user_id
            session['username'] = username
            session.permanent = True
            session['last_activity'] = time.time()
            update_last_login(user_id)
            log_login_success(user_id, 'user')
            return redirect(url_for('home_bp.homepage'))

        # Store pending 2FA state
        session['pending_2fa_user'] = user_id
        session['pending_2fa_username'] = username

        # Generate and send OTP
        otp_code = generate_otp()
        store_otp(user_id, otp_code)
        session['otp_created_at'] = time.time()
        sent, err = send_otp_email(user_email, otp_code)

        if not sent:
            # Email delivery failed, do NOT skip 2FA as this would silently
            # downgrade security. Clear the pending state and ask user to retry.
            session.pop('pending_2fa_user', None)
            session.pop('pending_2fa_username', None)
            flash("Could not send verification code. Please try again later.", "danger")
            return redirect(url_for('auth_bp.login_page'))

        return redirect(url_for('auth_bp.verify_2fa_page'))
    else:
        # Log failed login attempt for security monitoring
        log_login_failed(username, 'user')
        flash("Invalid username or password.", "danger")
        return redirect(url_for('auth_bp.login_page'))


@auth_bp.route('/logout')
def logout():
    # Log logout before clearing session
    if 'user_id' in session:
        log_logout(session['user_id'], 'user')
    # This clears the session data including the user_id and username
    # This logs out the user and returns them to the login page
    session.clear()
    return redirect(url_for('auth_bp.login_page'))


@auth_bp.route('/verify-2fa', methods=['GET'])
def verify_2fa_page():
    if 'pending_2fa_user' not in session:
        return redirect(url_for('auth_bp.login_page'))
    # Calculate true remaining seconds so the timer survives page refreshes
    created = session.get('otp_created_at', time.time())
    elapsed = time.time() - created
    remaining = max(0, 600 - int(elapsed))
    return render_template('verify_2fa.html', otp_remaining=remaining)


@auth_bp.route('/verify-2fa', methods=['POST'])
def verify_2fa():
    if 'pending_2fa_user' not in session:
        return redirect(url_for('auth_bp.login_page'))

    user_id = session['pending_2fa_user']
    username = session.get('pending_2fa_username', '')
    entered = request.form.get('otp_code', '').strip()

    success, reason = verify_otp(user_id, entered)

    if success:
        # Promote from pending to fully authenticated
        session.pop('pending_2fa_user', None)
        session.pop('pending_2fa_username', None)
        session['user_id'] = user_id
        session['username'] = username
        session.permanent = True
        session['last_activity'] = time.time()
        update_last_login(user_id)
        log_login_success(user_id, 'user')
        return redirect(url_for('home_bp.homepage'))

    if reason == 'max_attempts':
        session.pop('pending_2fa_user', None)
        session.pop('pending_2fa_username', None)
        log_login_failed(username, 'user')
        flash("Too many incorrect attempts. Please log in again.", "danger")
        return redirect(url_for('auth_bp.login_page'))

    if reason == 'expired':
        session.pop('pending_2fa_user', None)
        session.pop('pending_2fa_username', None)
        flash("Verification code has expired. Please log in again.", "warning")
        return redirect(url_for('auth_bp.login_page'))

    flash("Incorrect code. Please try again.", "danger")
    return redirect(url_for('auth_bp.verify_2fa_page'))


@auth_bp.route('/resend-2fa', methods=['POST'])
@limiter.limit("3 per minute")
def resend_2fa():
    if 'pending_2fa_user' not in session:
        return redirect(url_for('auth_bp.login_page'))

    user_id = session['pending_2fa_user']
    user_email = _get_user_email(user_id)

    if user_email:
        otp_code = generate_otp()
        if not store_otp(user_id, otp_code):
            flash("Could not generate verification code. Please try again.", "danger")
            return redirect(url_for('auth_bp.verify_2fa_page'))
        session['otp_created_at'] = time.time()
        success, error = send_otp_email(user_email, otp_code)
        if success:
            flash("A new verification code has been sent to your email.", "success")
        else:
            flash("Could not send verification code. Please try again.", "danger")
    else:
        flash("Could not resend code. Please log in again.", "danger")

    return redirect(url_for('auth_bp.verify_2fa_page'))


@auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    return render_template('forgot_password.html')


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")
def forgot_password():
    username = request.form.get('username', '').strip()
    user = find_by_username(username)

    if user:
        user_id = user[0]
        user_email = _get_user_email(user_id)

        if user_email:
            token = generate_reset_token()
            store_reset_token(user_id, token)
            # Build reset URL, require APP_BASE_URL in production to prevent Host header injection
            base_url = os.environ.get('APP_BASE_URL')
            if not base_url:
                if os.getenv("AWS_EXECUTION_ENV") or os.getenv("FLASK_ENV") == "production" or os.getenv("PRODUCTION"):
                    flash("Password reset is temporarily unavailable. Please contact support.", "danger")
                    return redirect(url_for('auth_bp.forgot_password_page'))
                base_url = request.host_url.rstrip('/')
            reset_path = url_for('auth_bp.reset_password_page', token=token)
            reset_url = base_url + reset_path
            send_password_reset_email(user_email, reset_url)

    # Always show the same message to prevent username enumeration
    flash("If that account exists, a password reset link has been sent.", "info")
    return redirect(url_for('auth_bp.forgot_password_page'))


@auth_bp.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    user_id = verify_reset_token(token)
    if user_id is None:
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for('auth_bp.login_page'))
    return render_template('reset_password.html', token=token)


@auth_bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    user_id = verify_reset_token(token)
    if user_id is None:
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for('auth_bp.login_page'))

    new_password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')

    valid, msg = validate_password(new_password)
    if not valid:
        flash(msg, "danger")
        return redirect(url_for('auth_bp.reset_password_page', token=token))

    if new_password != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for('auth_bp.reset_password_page', token=token))

    with get_db() as (conn, cur):
        cur.execute("""
            UPDATE users SET password = %s WHERE id = %s;
        """, (generate_password_hash(new_password), user_id))

    invalidate_reset_token(token)

    flash("Password updated. Please log in with your new password.", "success")
    return redirect(url_for('auth_bp.login_page'))


# The below 2 functions are core to GDPR regulations
# They allow users to access all information gathered about them
# and also allows them to delete there account

@pages_bp.route('/right_to_access', methods=['GET'])
@require_user_login
@audit_log('view', 'user_data')
def right_to_access():
    user_id = session['user_id']
    static_data, dynamic_data = get_user_data(user_id)
    log_dsr(user_id, session.get('username'), 'access')
    return render_template('access_data.html', static_data=static_data, dynamic_data=dynamic_data)


@pages_bp.route('/right_to_forget', methods=['POST'])
@require_user_login
@audit_log('delete', 'users')
def right_to_forget():
    user_id = session['user_id']
    password = request.form.get('password', '')

    # Verify the user's password before allowing account deletion
    user = find_by_id(user_id)
    if not user or not check_password_hash(user[1], password):
        flash('Incorrect password. Account deletion cancelled.', 'danger')
        return redirect(url_for('home_bp.homepage'))

    # Log DSR and deletion before actually deleting (for audit trail)
    log_dsr(user_id, session.get('username'), 'erasure')
    log_data_delete('users', user_id, {'action': 'right_to_forget', 'complete_deletion': True})
    delete_user(user_id)
    session.clear()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('auth_bp.login_page'))


@pages_bp.route('/delete_user_data', methods=['POST'])
@require_user_login
@audit_log('delete', 'submissions')
def delete_user_data():
    user_id = session['user_id']
    # Log DSR and data deletion
    log_dsr(user_id, session.get('username'), 'erasure')
    log_data_delete('submissions', user_id, {'action': 'delete_data_only', 'account_preserved': True})
    delete_user_data_only(user_id)
    return redirect(url_for('home_bp.homepage'))


# The below routes handle per client consent management.
# Users can view their consent status, withdraw consent (soft withdrawal
# that hides data from clients but keeps it), and re give consent.

@pages_bp.route('/consent', methods=['GET'])
@require_user_login
@audit_log('view', 'consent_status')
def consent_management():
    submissions = get_user_submissions(session['user_id'])
    return render_template('consent_management.html', submissions=submissions)


@pages_bp.route('/consent/withdraw/<int:submission_id>', methods=['POST'])
@require_user_login
@audit_log('update', 'submissions')
def withdraw_consent_route(submission_id):
    user_id = session['user_id']
    success = withdraw_consent(submission_id, user_id)

    if success:
        log_dsr(user_id, session.get('username'), 'consent_withdrawal')
        log_data_update('submissions', submission_id, {
            'action': 'consent_withdrawn',
            'user_id': user_id
        })
        flash("Consent withdrawn successfully. You can reinstate it at any time.", "warning")
    else:
        flash("Unable to withdraw consent. Submission not found.", "danger")

    return redirect(url_for('pages_bp.consent_management'))


@pages_bp.route('/consent/reinstate/<int:submission_id>', methods=['POST'])
@require_user_login
@audit_log('update', 'submissions')
def reinstate_consent_route(submission_id):
    user_id = session['user_id']
    success = reinstate_consent(submission_id, user_id)

    if success:
        log_dsr(user_id, session.get('username'), 'consent_reinstatement')
        log_data_update('submissions', submission_id, {
            'action': 'consent_reinstated',
            'user_id': user_id
        })
        flash("Consent reinstated. The organisation can access your data again.", "success")
    else:
        flash("Unable to reinstate consent. Submission not found.", "danger")

    return redirect(url_for('pages_bp.consent_management'))


@pages_bp.route('/delete_submission/<int:submission_id>', methods=['POST'])
@require_user_login
@audit_log('delete', 'submissions')
def delete_submission_route(submission_id):
    """
    Deletes a single questionnaire submission and all related data.
    Uses soft deletion for audit trail while hard deleting sensitive data.
    """
    user_id = session['user_id']
    result = delete_single_submission(submission_id, user_id)

    if result and result['success']:
        # Log deletion with full context for audit trail
        log_data_delete('submissions', submission_id, {
            'action': 'delete_single_submission',
            'user_id': user_id,
            'client_name': result['client_name'],
            'answers_deleted': result['answers_deleted'],
            'deletion_type': 'user_initiated'
        })
        flash(f"Submission for '{result['client_name']}' has been permanently deleted.", "success")
    else:
        flash("Unable to delete submission. Please try again.", "danger")

    # Redirect back to the referring page (consent management or edit page)
    return _safe_referrer_redirect(url_for('pages_bp.consent_management'))


@pages_bp.route('/privacy')
def privacy_policy():
    return render_template('privacy_policy.html', current_date=datetime.now(timezone.utc).strftime('%d %B %Y'))


@pages_bp.route('/dashboard')
@require_user_login
@audit_log('view', 'user_dashboard')
def user_dashboard():
    """User dashboard showing questionnaire stats, consent status, and DSR history."""
    user_id = session['user_id']
    stats = get_user_dashboard_stats(user_id)
    dsrs = get_dsrs_for_user(user_id)

    return render_template(
        'user_dashboard.html',
        stats=stats,
        dsrs=dsrs,
        username=session.get('username')
    )


@pages_bp.route('/export_data')
@require_user_login
@audit_log('export', 'user_data')
def export_user_data():
    """
    Export all user data as a CSV file
    """
    user_id = session['user_id']
    static_data, dynamic_data = get_user_data(user_id)

    output = io.StringIO()
    writer = csv.writer(output)

    # Core information section
    writer.writerow(['--- Core Information ---'])
    writer.writerow(['First Name', 'Address', 'Age'])
    for row in static_data:
        writer.writerow([row[0], row[1], row[2]])

    writer.writerow([])

    # Per organisation data section
    if dynamic_data:
        writer.writerow(['--- Questionnaire Data ---'])
        writer.writerow(['Organisation', 'Field Label', 'Category', 'Value', 'Consent Status'])
        for row in dynamic_data:
            consent_status = 'Withdrawn' if row[4] else 'Active'
            writer.writerow([row[0], row[1], row[2], row[3], consent_status])

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    log_dsr(user_id, session.get('username'), 'portability')
    log_data_export(user_id, 'csv', {'action': 'user_data_portability'})

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=my_data_{timestamp}.csv'
        }
    )
