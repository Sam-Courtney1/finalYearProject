from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from application.services.log_form_data import handle_questionnaire_submission
from data.client_database import get_db_connection
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
@questionnaire_bp.route('/questionnaire/<int:client_id>', methods = ['GET', 'POST'])
@audit_log('view', 'questionnaire_fields')
def questionnaire_form(client_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        pass

    if request.method == 'POST':
        user_id = session['user_id']
        handle_questionnaire_submission(user_id, client_id, request.form)
        # Log questionnaire submission
        log_data_create('questionnaire_submission', user_id, {
            'client_id': client_id,
            'fields_submitted': len([k for k in request.form.keys() if k != 'client_id'])
        })
        return redirect(url_for('home_bp.homepage'))
    else:
        pass

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                SELECT field_id, field_label, field_type, category
                FROM questionnaire_fields
                WHERE client_id = %s
                ORDER BY field_id;
                """, (client_id,))
    
    fields = cur.fetchall()
    cur.close()
    conn.close()

    # Redundant for now as I want core info to only appear once
    # No longer appears in questionnaires as a must answer field
    # Not removing yet as it will be used in the coming weeks
    static_fields = []

    return render_template(
        'questionnaire.html',
        static_fields = static_fields,
        dynamic_fields = fields,
        client_id = client_id
    )

@questionnaire_bp.route('/questionnaire', methods = ['POST'])
def submit_questionnaire():
    # If somehow the user gets to this page and is not logged in
    # Then no use_id will be in session so return them to be logged in
    # Double security as users cannot type in the url extension to get to this page
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        pass
    # Adding in client id so the form is linked to the correct client
    client_id = int(request.form["client_id"])
    handle_questionnaire_submission(session['user_id'], client_id,request.form)
    # Log questionnaire submission
    log_data_create('questionnaire_submission', session['user_id'], {
        'client_id': client_id,
        'fields_submitted': len([k for k in request.form.keys() if k != 'client_id'])
    })
    return redirect(url_for('home_bp.homepage'))

"""
The below function passes a list of clinets to the questionnare selection page
This is the page with the drop down menu, this is how that menu is populated
"""
@questionnaire_bp.route('/questionnaire', methods=['GET'])
@audit_log('view', 'questionnaire_selection')
def select_client():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        pass

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT client_id, username FROM clients ORDER BY username;")
    clients = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('questionnaire_select.html', clients = clients)


"""
The below routes allow users to edit their previously submitted questionnaire answers.
The user first selects which client's submission to edit, then sees a pre-populated
form with their current answers (decrypted), and can save changes.
"""

@questionnaire_bp.route('/edit', methods=['GET'])
@audit_log('view', 'submissions')
def select_submission_to_edit():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))

    submissions = get_user_submissions(session['user_id'])
    return render_template('edit_select.html', submissions=submissions)


@questionnaire_bp.route('/edit/<int:submission_id>', methods=['GET'])
@audit_log('view', 'answers')
def edit_submission(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))

    answers = get_submission_answers(submission_id, session['user_id'])
    if answers is None:
        flash("Submission not found or access denied.")
        return redirect(url_for('questionnaire_bp.select_submission_to_edit'))

    return render_template('edit_answers.html', fields=answers, submission_id=submission_id)


@questionnaire_bp.route('/edit/<int:submission_id>', methods=['POST'])
@audit_log('update', 'answers')
def save_edited_submission(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))

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
