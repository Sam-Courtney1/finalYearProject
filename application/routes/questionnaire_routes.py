from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from application.services.decorators import require_user_login
from application.services.log_form_data import handle_questionnaire_submission
from data.db_connection import get_db
from application.services.audit_service import audit_log, log_data_create, log_data_update
from data.submission_database import get_user_submissions, get_submission_answers, update_submission_answers

"""
questionnaire_bp is an object of Blueprint that stores its name (questionnaire_bp) 
The module where it is definined is inside of __name__
And all routes that belong to it
"""

questionnaire_bp = Blueprint('questionnaire_bp', __name__)

"""
Below are all the routes and actions that are assigned to questionnaire_bp
These include displaying pages to users and allowing them to login and register


The questionnaire_form accepts an arugment of client id to identify which companies
form it is processing. If a post request is recieved then the form will send the data to 
the server to be processed and if it recieves a get request it will display the questionaire page
"""
@questionnaire_bp.route('/questionnaire/<int:client_id>/<questionnaire_name>', methods = ['GET', 'POST'])
@require_user_login
@audit_log('view', 'questionnaire_fields')
def questionnaire_form(client_id, questionnaire_name):
    """
    Display and submit a specific questionnaire for a client.
    URL now includes questionnaire_name to distinguish between multiple questionnaires.
    """

    if request.method == 'POST':
        user_id = session['user_id']
        handle_questionnaire_submission(user_id, client_id, questionnaire_name, request.form)
        # Log questionnaire submission
        log_data_create('questionnaire_submission', user_id, {
            'client_id': client_id,
            'questionnaire_name': questionnaire_name,
            'fields_submitted': len([k for k in request.form.keys() if k != 'client_id'])
        })
        flash(f"Questionnaire '{questionnaire_name}' submitted successfully!")
        return redirect(url_for('home_bp.homepage'))

    # GET request: fetch fields for this specific questionnaire
    with get_db() as (conn, cur):
        cur.execute("""
                    SELECT field_id, field_label, field_type, category
                    FROM questionnaire_fields
                    WHERE client_id = %s AND questionnaire_name = %s
                    ORDER BY field_id;
                    """, (client_id, questionnaire_name))

        fields = cur.fetchall()

        # Get client name for display
        cur.execute("SELECT username FROM clients WHERE client_id = %s", (client_id,))
        client_name_row = cur.fetchone()
        client_name = client_name_row[0] if client_name_row else "Unknown"

    # Redundant for now as I want core info to only appear once
    # No longer appears in questionnaires as a must answer field
    # Not removing yet as it will be used in the coming weeks
    static_fields = []

    return render_template(
        'questionnaire.html',
        static_fields = static_fields,
        dynamic_fields = fields,
        client_id = client_id,
        questionnaire_name = questionnaire_name,
        client_name = client_name
    )

# Note: The old /questionnaire POST route is now redundant
# Submissions are handled by the route above with client_id and questionnaire_name

"""
The below function shows all available questionnaires grouped by client/organization.
Displays organization name with their available questionnaires.
"""
@questionnaire_bp.route('/questionnaire', methods=['GET'])
@require_user_login
@audit_log('view', 'questionnaire_selection')
def select_questionnaire():

    with get_db() as (conn, cur):
        # Get all distinct questionnaires with client info
        cur.execute("""
            SELECT DISTINCT c.client_id, c.username, qf.questionnaire_name
            FROM clients c
            JOIN questionnaire_fields qf ON c.client_id = qf.client_id
            ORDER BY c.username, qf.questionnaire_name;
        """)

        questionnaires = cur.fetchall()

    # Group by client for better UX
    clients_dict = {}
    for client_id, client_name, q_name in questionnaires:
        if client_name not in clients_dict:
            clients_dict[client_name] = {
                'client_id': client_id,
                'questionnaires': []
            }
        clients_dict[client_name]['questionnaires'].append(q_name)

    return render_template('questionnaire_select.html', clients = clients_dict)


"""
The below routes allow users to edit their previously submitted questionnaire answers.
The user first selects which client's submission to edit, then sees a pre-populated
form with their current answers (decrypted), and can save changes.
"""

@questionnaire_bp.route('/edit', methods=['GET'])
@require_user_login
@audit_log('view', 'submissions')
def select_submission_to_edit():
    submissions = get_user_submissions(session['user_id'])
    return render_template('edit_select.html', submissions=submissions)


@questionnaire_bp.route('/edit/<int:submission_id>', methods=['GET'])
@require_user_login
@audit_log('view', 'answers')
def edit_submission(submission_id):
    answers = get_submission_answers(submission_id, session['user_id'])
    if answers is None:
        flash("Submission not found or access denied.")
        return redirect(url_for('questionnaire_bp.select_submission_to_edit'))

    return render_template('edit_answers.html', fields=answers, submission_id=submission_id)


@questionnaire_bp.route('/edit/<int:submission_id>', methods=['POST'])
@require_user_login
@audit_log('update', 'answers')
def save_edited_submission(submission_id):
    user_id = session['user_id']

    # Build dict of {field_id: new_value} from the form
    updated_fields = {}
    for key_name, value in request.form.items():
        if key_name.startswith("field_"):
            field_id = key_name.split("_")[1]
            updated_fields[field_id] = value

    count = update_submission_answers(submission_id, user_id, updated_fields)

    if count is None:
        flash("Submission not found or access denied.")
        return redirect(url_for('questionnaire_bp.select_submission_to_edit'))

    log_data_update('answers', submission_id, {
        'action': 'questionnaire_edit',
        'fields_updated': count,
        'field_ids': list(updated_fields.keys())
    })

    flash(f"Your answers have been updated ({count} field(s) changed).")
    return redirect(url_for('pages_bp.right_to_access'))
