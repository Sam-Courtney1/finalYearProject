from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from application.services.authentication import register_user, authenticate_user
from data.user_database import find_by_username, get_user_data, delete_user, delete_user_data_only
from data.db_connection import get_db_connection
from application.services.audit_service import (
    audit_log, log_login_success, log_login_failed, log_logout,
    log_data_create, log_data_delete, log_data_update
)
from data.submission_database import get_user_submissions, withdraw_consent, reinstate_consent, delete_single_submission
import os

"""
auth_bp is an object of Blueprint that stores its name (auth_bp) 
The module where it is definined is inside of __name__
And all routes that belong to it
"""

auth_bp = Blueprint('auth_bp', __name__)
pages_bp = Blueprint('pages_bp', __name__)

# Below are all the routes and actions that are assigned to auth_bp
# These include displaying pages to users and allowing them to login and register

@auth_bp.route('/')
def login_page():
    return render_template('landing.html')

@auth_bp.route('/register')
def register_page():
    return render_template('Register.html')

@auth_bp.route('/register_user', methods = ['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    age        = request.form['age']
    address    = request.form['address']

    # Check to see if username already exists
    existing_user = find_by_username(username)
    if existing_user:
        flash("Username already exists. Please choose another.")
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

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO submissions (user_id, client_id, consent)
        VALUES (%s, NULL, FALSE)
        RETURNING submission_id;
    """, (user_id,))
    submission_id = cur.fetchone()[0]

    key = os.getenv("APP_ENC_KEY")

    cur.execute("""
        INSERT INTO pii (submission_id, first_name_enc, address_enc)
        VALUES (%s, pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s));
    """, (submission_id, username, key, address, key))

    cur.execute("""
        INSERT INTO demographic_data (submission_id, age)
        VALUES (%s, %s);
    """, (submission_id, age))

    conn.commit()
    cur.close()
    conn.close()

    # Log new user registration
    log_data_create('users', user_id, {'action': 'registration'})
    log_login_success(user_id, 'user')

    return redirect(url_for('home_bp.homepage'))



@auth_bp.route('/login', methods = ['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    # Make a call to the authenticate_user function and the user_id
    # of the linked account is stored in user_id
    user_id = authenticate_user(username, password)
    if user_id:
        session['user_id'] = user_id
        session['username'] = username
        # Log successful login for audit trail
        log_login_success(user_id, 'user')
        return redirect(url_for('home_bp.homepage'))
    else:
        # Log failed login attempt for security monitoring
        log_login_failed(username, 'user')
        flash("Username or password is incorrect. Please register an account or login with valid credentials")
        return redirect(url_for('auth_bp.login_page'))

@auth_bp.route('/logout')
def logout():
    # Log logout before clearing session (need user_id)
    if 'user_id' in session:
        log_logout(session['user_id'], 'user')
    # This clears the session data including the user_id and username
    # This logs out the user and returns them to the login page
    session.clear()
    return redirect(url_for('auth_bp.login_page'))

"""
The below 2 functions are core to GDPR regulations
They allow users to access all information gathered about them
and also allows them to delete there account
"""

@pages_bp.route('/right_to_access', methods = ['GET'])
@audit_log('view', 'user_data')
def right_to_access():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        user_id = session['user_id']

    static_data, dynamic_data = get_user_data(user_id)
    return render_template('access_data.html', static_data = static_data, dynamic_data = dynamic_data)



@pages_bp.route('/right_to_forget', methods = ['POST'])
@audit_log('delete', 'users')
def right_to_forget():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        user_id = session['user_id']

    # Log deletion before actually deleting (for audit trail)
    log_data_delete('users', user_id, {'action': 'right_to_forget', 'complete_deletion': True})
    delete_user(user_id)
    session.clear()
    return redirect(url_for('auth_bp.login_page'))

@pages_bp.route('/delete_user_data', methods=['POST'])
@audit_log('delete', 'submissions')
def delete_user_data():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        user_id = session['user_id']

    # Log data deletion
    log_data_delete('submissions', user_id, {'action': 'delete_data_only', 'account_preserved': True})
    delete_user_data_only(user_id)
    return redirect(url_for('home_bp.homepage'))


"""
The below routes handle per-client consent management.
Users can view their consent status, withdraw consent (soft withdrawal
that hides data from clients but keeps it), and re-give consent.
"""

@pages_bp.route('/consent', methods=['GET'])
@audit_log('view', 'consent_status')
def consent_management():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))

    submissions = get_user_submissions(session['user_id'])
    return render_template('consent_management.html', submissions=submissions)


@pages_bp.route('/consent/withdraw/<int:submission_id>', methods=['POST'])
@audit_log('update', 'submissions')
def withdraw_consent_route(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))

    user_id = session['user_id']
    success = withdraw_consent(submission_id, user_id)

    if success:
        log_data_update('submissions', submission_id, {
            'action': 'consent_withdrawn',
            'user_id': user_id
        })
        flash("Consent withdrawn. The organisation can no longer access your data.")
    else:
        flash("Could not withdraw consent. Submission not found.")

    return redirect(url_for('pages_bp.consent_management'))


@pages_bp.route('/consent/reinstate/<int:submission_id>', methods=['POST'])
@audit_log('update', 'submissions')
def reinstate_consent_route(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))

    user_id = session['user_id']
    success = reinstate_consent(submission_id, user_id)

    if success:
        log_data_update('submissions', submission_id, {
            'action': 'consent_reinstated',
            'user_id': user_id
        })
        flash("Consent re-given. The organisation can now access your data again.")
    else:
        flash("Could not reinstate consent. Submission not found.")

    return redirect(url_for('pages_bp.consent_management'))


@pages_bp.route('/delete_submission/<int:submission_id>', methods=['POST'])
@audit_log('delete', 'submissions')
def delete_submission_route(submission_id):
    """
    Deletes a single questionnaire submission and all related data.
    Uses soft deletion for audit trail while hard deleting sensitive data.
    """
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))

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
        flash(f"Submission for '{result['client_name']}' has been permanently deleted.")
    else:
        flash("Could not delete submission. Submission not found or access denied.")

    # Redirect back to the referring page (consent management or edit page)
    return redirect(request.referrer or url_for('pages_bp.consent_management'))
