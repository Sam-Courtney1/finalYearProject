from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from application.services.decorators import require_client_login
from application.services.authentication import validate_password
from application.extensions import limiter
from data.client_database import insert_client, find_client_by_username
from data.questionnaire_client import insert_field, get_fields_for_client, delete_field, get_questionnaires_for_client, questionnaire_name_exists
from data.submission_database import get_submissions_for_questionnaire
from application.services.audit_service import (
    log_login_success, log_login_failed, log_logout,
    log_data_create, log_data_delete, log_data_access
)

"""
client_bp is a Blueprint that handles all client/owner-side routes.
These routes are registered with a /client prefix in wsgi.py.

Clients are the business owners who create questionnaires,
separate from end users who fill them out.
"""

client_bp = Blueprint('client_bp', __name__)

@client_bp.route("/", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def client_login():
    """
    Client login page.
    GET: Display the login form
    POST: Authenticate the client
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        client = find_client_by_username(username)
        if client and check_password_hash(client[2], password):
            session["client_id"] = client[0]
            session["client_username"] = client[1]
            # Log successful client login
            log_login_success(client[0], 'client')
            return redirect(url_for("client_bp.client_dashboard"))
        else:
            # Log failed client login attempt
            log_login_failed(username, 'client')
            flash("Invalid username or password.")
            return render_template("client_landing.html")
    else:
        return render_template("client_landing.html")


@client_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def client_register():
    """
    Client registration page.
    GET: Display the registration form
    POST: Create a new client account
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        valid, msg = validate_password(password)
        if not valid:
            flash(msg)
            return render_template("client_register.html")

        duplicate = find_client_by_username(username)
        if duplicate:
            flash("Username already exists. Please choose another.")
            return render_template("client_register.html")

        password_hash = generate_password_hash(password)
        client_id = insert_client(username, password_hash)
        session["client_id"] = client_id
        session["client_username"] = username

        # Log new client registration
        log_data_create('clients', client_id, {'action': 'registration'})
        log_login_success(client_id, 'client')

        return redirect(url_for("client_bp.client_dashboard"))
    else:
        return render_template("client_register.html")


@client_bp.route("/logout")
def client_logout():
    """
    Clear the client session and redirect to login.
    """
    # Log logout before clearing session
    if "client_id" in session:
        log_logout(session["client_id"], 'client')
    session.clear()
    return redirect(url_for("client_bp.client_login"))


@client_bp.route("/dashboard")
@require_client_login
def client_dashboard():
    return render_template(
        "client_dashboard.html",
        username=session.get("client_username")
    )


@client_bp.route("/questionnaires", methods=["GET"])
@require_client_login
def client_questionnaire_list():
    """
    Shows all questionnaires for this client with ability to create new ones.
    """
    client_id = session["client_id"]
    questionnaires = get_questionnaires_for_client(client_id)

    return render_template("client_questionnaire_list.html", questionnaires=questionnaires)


@client_bp.route("/questionnaire/create", methods=["GET", "POST"])
@require_client_login
def client_create_questionnaire():
    """
    Create a new questionnaire (just the name initially).
    """
    if request.method == "POST":
        questionnaire_name = request.form["questionnaire_name"].strip()
        client_id = session["client_id"]

        if not questionnaire_name:
            flash("Questionnaire name cannot be empty.", "danger")
            return render_template("client_create_questionnaire.html")

        # Check if name already exists for this client
        if questionnaire_name_exists(client_id, questionnaire_name):
            flash(f"A questionnaire named '{questionnaire_name}' already exists. Please choose a different name.", "danger")
            return render_template("client_create_questionnaire.html")

        flash(f"Questionnaire '{questionnaire_name}' created successfully! Now add fields below.", "success")
        return redirect(url_for("client_bp.client_questionnaire_editor", questionnaire_name=questionnaire_name))

    return render_template("client_create_questionnaire.html")


@client_bp.route("/questionnaire/<questionnaire_name>", methods=["GET", "POST"])
@require_client_login
def client_questionnaire_editor(questionnaire_name):
    """
    Questionnaire field editor for a specific questionnaire.
    GET: Display the questionnaire editor with existing fields
    POST: Add a new field to the questionnaire
    """
    client_id = session["client_id"]

    if request.method == "POST":
        label = request.form["label"]
        field_type = request.form["field_type"]
        category = request.form["category"]

        # Whitelist allowed values to prevent injection of unexpected types
        allowed_field_types = {'text', 'number'}
        allowed_categories = {'PII', 'Medical', 'Demographic'}

        if field_type not in allowed_field_types:
            flash("Invalid field type.", "danger")
            return redirect(url_for("client_bp.client_questionnaire_editor", questionnaire_name=questionnaire_name))

        if category not in allowed_categories:
            flash("Invalid category.", "danger")
            return redirect(url_for("client_bp.client_questionnaire_editor", questionnaire_name=questionnaire_name))

        insert_field(client_id, questionnaire_name, label, field_type, category)

        # Log questionnaire field creation
        log_data_create('questionnaire_fields', client_id, {
            'questionnaire_name': questionnaire_name,
            'label': label,
            'field_type': field_type,
            'category': category
        })

        flash(f"Field '{label}' added successfully.", "success")
        return redirect(url_for("client_bp.client_questionnaire_editor", questionnaire_name=questionnaire_name))
    else:
        fields = get_fields_for_client(client_id, questionnaire_name)
        return render_template("client_questionnaire.html",
                               fields=fields,
                               questionnaire_name=questionnaire_name)


@client_bp.route("/delete_field/<int:field_id>", methods=["POST"])
@require_client_login
def client_delete_field(field_id):
    """
    Delete a field from the client's questionnaire.
    """
    client_id = session["client_id"]
    # Log field deletion before deleting
    log_data_delete('questionnaire_fields', field_id, {'client_id': client_id})
    delete_field(field_id, client_id)
    # Redirect back to referring page (the questionnaire editor)
    return redirect(request.referrer or url_for("client_bp.client_questionnaire_list"))


@client_bp.route("/questionnaire/<questionnaire_name>/data", methods=["GET"])
@require_client_login
def client_view_submissions(questionnaire_name):
    """
    View anonymised submission data for a specific questionnaire.
    Shows all fields except Hashed, with respondents anonymised as
    'Respondent 1', 'Respondent 2', etc.
    Only shows data where consent is active and submission is not deleted.
    """
    client_id = session["client_id"]

    # Verify the questionnaire belongs to this client
    if not questionnaire_name_exists(client_id, questionnaire_name):
        flash("Questionnaire not found.")
        return redirect(url_for("client_bp.client_questionnaire_list"))

    column_headers, submissions_data = get_submissions_for_questionnaire(
        client_id, questionnaire_name
    )

    # Audit log: client is viewing submission data (GDPR Art. 30)
    log_data_access(client_id, 'submissions', details={
        'action': 'client_view_submissions',
        'questionnaire_name': questionnaire_name,
        'respondent_count': len(submissions_data)
    })

    return render_template(
        "client_view_submissions.html",
        questionnaire_name=questionnaire_name,
        column_headers=column_headers,
        submissions=submissions_data
    )
