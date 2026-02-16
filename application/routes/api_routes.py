from flask import Blueprint, request, jsonify, session
from functools import wraps
from application.services.jwt_utils import create_token, decode_token
from application.services.authentication import register_user, authenticate_user
from data.user_database import find_by_username, get_user_data, delete_user, delete_user_data_only
from data.db_connection import get_db_connection
from application.services.log_form_data import handle_questionnaire_submission
from application.services.audit_service import (
    audit_log, log_login_success, log_login_failed, log_logout,
    log_data_create, log_data_delete, log_data_update
)
from data.submission_database import (
    get_user_submissions, get_submission_answers, update_submission_answers,
    withdraw_consent, reinstate_consent, delete_single_submission
)
import os

"""
API routes for the mobile app
These return JSON instead of HTML so the React Native app can use them
All routes start with /api/ and use JWT tokens instead of browser cookies for auth
"""

api_bp = Blueprint('api_bp', __name__)


def token_required(f):
    """
    Checks the JWT token sent from the mobile app in the request header
    If valid, puts user info into session so audit logging still works
    If invalid or missing, returns a 401 error
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        # Get the token from the header and decode it
        token = auth_header.split(' ', 1)[1]
        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Put user info into session so audit_service functions can read it
        session['user_id'] = payload['user_id']
        session['username'] = payload['username']

        return f(*args, **kwargs)
    return wrapper


# Auth endpoints

@api_bp.route('/register', methods=['POST'])
def api_register():
    """Registers a new user, same logic as the web register route"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    username = data.get('username')
    password = data.get('password')
    age = data.get('age')
    address = data.get('address')

    if not all([username, password, age, address]):
        return jsonify({"error": "username, password, age, and address are required"}), 400

    # Check if the username is already taken
    existing = find_by_username(username)
    if existing:
        return jsonify({"error": "Username already exists"}), 409

    # Hash the password and insert the user into the database
    register_user(username, password)

    # Get the new user_id back from the database
    user = find_by_username(username)
    if not user:
        return jsonify({"error": "Registration failed"}), 500

    user_id = user[0]

    # Set session so audit logging works for this request
    session['user_id'] = user_id
    session['username'] = username

    # Insert submission, encrypted PII and demographic records
    # Same SQL as the register route in pages_and_actions.py
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO submissions (user_id, client_id, consent)
        VALUES (%s, NULL, FALSE) RETURNING submission_id;
    """, (user_id,))
    submission_id = cur.fetchone()[0]

    key = os.getenv("APP_ENC_KEY")

    # Encrypt name and address before storing
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

    # Log the registration and login for the audit trail
    log_data_create('users', user_id, {'action': 'registration', 'source': 'mobile_api'})
    log_login_success(user_id, 'user')

    # Return a JWT token so the mobile app can make future requests
    token = create_token(user_id, username)
    return jsonify({"token": token, "user_id": user_id, "username": username}), 201


@api_bp.route('/login', methods=['POST'])
def api_login():
    """Checks username and password, returns a JWT token if valid"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    # authenticate_user returns the user_id if correct, None if not
    user_id = authenticate_user(username, password)
    if user_id:
        session['user_id'] = user_id
        session['username'] = username
        log_login_success(user_id, 'user')
        token = create_token(user_id, username)
        return jsonify({"token": token, "user_id": user_id, "username": username}), 200
    else:
        log_login_failed(username, 'user')
        return jsonify({"error": "Invalid username or password"}), 401


@api_bp.route('/logout', methods=['POST'])
@token_required
def api_logout():
    """Logs the logout event, the mobile app deletes the token on its side"""
    user_id = session['user_id']
    log_logout(user_id, 'user')
    return jsonify({"message": "Logged out successfully"}), 200


# GDPR rights endpoints

@api_bp.route('/user/data', methods=['GET'])
@token_required
@audit_log('view', 'user_data')
def api_user_data():
    """Returns all data stored about the user as JSON (Right to Access, GDPR Article 15)"""
    user_id = session['user_id']
    static_data, dynamic_data = get_user_data(user_id)

    # Convert database rows into dictionaries for JSON
    static_list = []
    for row in static_data:
        static_list.append({
            "first_name": row[0],
            "address": row[1],
            "age": row[2]
        })

    # Group questionnaire answers by company so the app can show them separately
    companies = {}
    for row in dynamic_data:
        company = row[0]
        if company not in companies:
            companies[company] = []
        companies[company].append({
            "field_label": row[1],
            "category": row[2],
            "value": row[3]
        })

    return jsonify({"static_data": static_list, "dynamic_data": companies}), 200


@api_bp.route('/user/account', methods=['DELETE'])
@token_required
@audit_log('delete', 'users')
def api_delete_account():
    """Deletes the user account and all their data (Right to Forget, GDPR Article 17)"""
    user_id = session['user_id']
    log_data_delete('users', user_id, {'action': 'right_to_forget', 'complete_deletion': True, 'source': 'mobile_api'})
    delete_user(user_id)
    return jsonify({"message": "Account and all data deleted"}), 200


@api_bp.route('/user/data', methods=['DELETE'])
@token_required
@audit_log('delete', 'submissions')
def api_delete_data():
    """Deletes the users questionnaire data but keeps their account active"""
    user_id = session['user_id']
    log_data_delete('submissions', user_id, {'action': 'delete_data_only', 'account_preserved': True, 'source': 'mobile_api'})
    delete_user_data_only(user_id)
    return jsonify({"message": "Data deleted, account preserved"}), 200


# Questionnaire endpoints

@api_bp.route('/clients', methods=['GET'])
@token_required
@audit_log('view', 'questionnaire_selection')
def api_list_clients():
    """
    Returns list of all organizations with their questionnaires.
    Format: [{"client_id": 1, "name": "HSE", "questionnaires": ["Cardio Health", "Diabetes Study"]}, ...]
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Get all distinct questionnaires with client info
    cur.execute("""
        SELECT DISTINCT c.client_id, c.username, qf.questionnaire_name
        FROM clients c
        JOIN questionnaire_fields qf ON c.client_id = qf.client_id
        ORDER BY c.username, qf.questionnaire_name;
    """)

    results = cur.fetchall()
    cur.close()
    conn.close()

    # Group questionnaires by client
    clients_dict = {}
    for client_id, client_name, q_name in results:
        if client_id not in clients_dict:
            clients_dict[client_id] = {
                "client_id": client_id,
                "name": client_name,
                "questionnaires": []
            }
        clients_dict[client_id]["questionnaires"].append(q_name)

    client_list = list(clients_dict.values())
    return jsonify({"clients": client_list}), 200


@api_bp.route('/questionnaire/<int:client_id>/<questionnaire_name>', methods=['GET'])
@token_required
@audit_log('view', 'questionnaire_fields')
def api_get_questionnaire(client_id, questionnaire_name):
    """
    Returns the questionnaire fields for a specific client's specific questionnaire.
    Mobile app uses this to build the form.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT field_id, field_label, field_type, category
        FROM questionnaire_fields
        WHERE client_id = %s AND questionnaire_name = %s
        ORDER BY field_id;
    """, (client_id, questionnaire_name))
    fields = cur.fetchall()
    cur.close()
    conn.close()

    field_list = [{
        "field_id": f[0],
        "field_label": f[1],
        "field_type": f[2],
        "category": f[3]
    } for f in fields]

    return jsonify({
        "client_id": client_id,
        "questionnaire_name": questionnaire_name,
        "fields": field_list
    }), 200


@api_bp.route('/questionnaire/<int:client_id>/<questionnaire_name>', methods=['POST'])
@token_required
def api_submit_questionnaire(client_id, questionnaire_name):
    """
    Submits questionnaire answers for a specific client's specific questionnaire.
    Request body: {"consent": true, "fields": {"field_id": "value", ...}}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if not data.get('consent'):
        return jsonify({"error": "Consent is required"}), 400

    user_id = session['user_id']

    # Build form dict in the format handle_questionnaire_submission expects
    form_dict = {}
    fields = data.get('fields', {})
    for field_id, value in fields.items():
        form_dict[f"field_{field_id}"] = value
    form_dict['consent'] = 'on'

    handle_questionnaire_submission(user_id, client_id, questionnaire_name, form_dict)

    log_data_create('questionnaire_submission', user_id, {
        'client_id': client_id,
        'questionnaire_name': questionnaire_name,
        'fields_submitted': len(fields),
        'source': 'mobile_api'
    })

    return jsonify({"message": "Questionnaire submitted successfully"}), 201


# Edit answers endpoints

@api_bp.route('/submissions', methods=['GET'])
@token_required
@audit_log('view', 'submissions')
def api_list_submissions():
    """Returns list of user's questionnaire submissions with client info and questionnaire names"""
    user_id = session['user_id']
    submissions = get_user_submissions(user_id)

    submission_list = [{
        "submission_id": s[0],
        "client_id": s[1],
        "client_name": s[2],
        "consent_withdrawn": s[3],
        "questionnaire_name": s[4]
    } for s in submissions]

    return jsonify({"submissions": submission_list}), 200


@api_bp.route('/submissions/<int:submission_id>/answers', methods=['GET'])
@token_required
@audit_log('view', 'answers')
def api_get_submission_answers(submission_id):
    """Returns current decrypted answers for a submission (excluding Hashed fields)"""
    user_id = session['user_id']
    answers = get_submission_answers(submission_id, user_id)

    if answers is None:
        return jsonify({"error": "Submission not found or access denied"}), 404

    field_list = [{
        "field_id": a[0],
        "field_label": a[1],
        "field_type": a[2],
        "category": a[3],
        "value": a[4]
    } for a in answers]

    return jsonify({"submission_id": submission_id, "fields": field_list}), 200


@api_bp.route('/submissions/<int:submission_id>/answers', methods=['PUT'])
@token_required
@audit_log('update', 'answers')
def api_update_submission_answers(submission_id):
    """
    Updates answers for a submission.
    Request body: {"fields": {"<field_id>": "<new_value>", ...}}
    """
    data = request.get_json()
    if not data or 'fields' not in data:
        return jsonify({"error": "Request body must contain 'fields' dict"}), 400

    user_id = session['user_id']
    updated_fields = data['fields']

    count = update_submission_answers(submission_id, user_id, updated_fields)

    if count is None:
        return jsonify({"error": "Submission not found or access denied"}), 404

    log_data_update('answers', submission_id, {
        'action': 'questionnaire_edit',
        'fields_updated': count,
        'field_ids': list(updated_fields.keys()),
        'source': 'mobile_api'
    })

    return jsonify({"message": "Answers updated", "fields_updated": count}), 200


# Consent management endpoints

@api_bp.route('/consent', methods=['GET'])
@token_required
@audit_log('view', 'consent_status')
def api_list_consent_status():
    """Returns consent status for all of user's submissions with questionnaire names"""
    user_id = session['user_id']
    submissions = get_user_submissions(user_id)

    consent_list = [{
        "submission_id": s[0],
        "client_id": s[1],
        "client_name": s[2],
        "consent_withdrawn": s[3],
        "questionnaire_name": s[4]
    } for s in submissions]

    return jsonify({"consents": consent_list}), 200


@api_bp.route('/submissions/<int:submission_id>/consent/withdraw', methods=['POST'])
@token_required
@audit_log('update', 'submissions')
def api_withdraw_consent(submission_id):
    """Withdraws consent for a specific submission"""
    user_id = session['user_id']
    success = withdraw_consent(submission_id, user_id)

    if not success:
        return jsonify({"error": "Submission not found or access denied"}), 404

    log_data_update('submissions', submission_id, {
        'action': 'consent_withdrawn',
        'user_id': user_id,
        'source': 'mobile_api'
    })

    return jsonify({"message": "Consent withdrawn"}), 200


@api_bp.route('/submissions/<int:submission_id>/consent/reinstate', methods=['POST'])
@token_required
@audit_log('update', 'submissions')
def api_reinstate_consent(submission_id):
    """Re-gives consent for a previously withdrawn submission"""
    user_id = session['user_id']
    success = reinstate_consent(submission_id, user_id)

    if not success:
        return jsonify({"error": "Submission not found or access denied"}), 404

    log_data_update('submissions', submission_id, {
        'action': 'consent_reinstated',
        'user_id': user_id,
        'source': 'mobile_api'
    })

    return jsonify({"message": "Consent reinstated"}), 200


@api_bp.route('/submissions/<int:submission_id>', methods=['DELETE'])
@token_required
@audit_log('delete', 'submissions')
def api_delete_submission(submission_id):
    """
    Deletes a single submission and all related data (mobile API version).
    DELETE /api/submissions/<submission_id>
    Returns: 200 with success message, or 404 if not found/access denied
    """
    user_id = session['user_id']
    result = delete_single_submission(submission_id, user_id)

    if result and result['success']:
        log_data_delete('submissions', submission_id, {
            'action': 'delete_single_submission',
            'user_id': user_id,
            'client_name': result['client_name'],
            'answers_deleted': result['answers_deleted'],
            'deletion_type': 'user_initiated',
            'source': 'mobile_api'
        })
        return jsonify({
            "message": f"Submission for '{result['client_name']}' deleted successfully",
            "client_name": result['client_name']
        }), 200
    else:
        return jsonify({"error": "Submission not found or access denied"}), 404
