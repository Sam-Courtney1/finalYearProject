from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from data.client_database import insert_client, find_client_by_username
from data.questionnaire_client import insert_field, get_fields_for_client, delete_field
from application.services.audit_service import (
    log_login_success, log_login_failed, log_logout,
    log_data_create, log_data_delete
)

"""
client_bp is a Blueprint that handles all client/owner-side routes.
These routes are registered with a /client prefix in wsgi.py.

Clients are the business owners who create questionnaires,
separate from end users who fill them out.
"""

client_bp = Blueprint('client_bp', __name__)

@client_bp.route("/", methods=["GET", "POST"])
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
            return render_template("client_login.html")
    else:
        return render_template("client_login.html")


@client_bp.route("/register", methods=["GET", "POST"])
def client_register():
    """
    Client registration page.
    GET: Display the registration form
    POST: Create a new client account
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

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
def client_dashboard():
    
    if "client_id" not in session:
        return redirect(url_for("client_bp.client_login"))

    return render_template(
        "client_dashboard.html",
        username=session.get("client_username")
    )


@client_bp.route("/questionnaire", methods=["GET", "POST"])
def client_questionnaire():
    """
    Questionnaire editor for clients to add/view fields.
    GET: Display the questionnaire editor with existing fields
    POST: Add a new field to the questionnaire
    """
    if "client_id" not in session:
        return redirect(url_for("client_bp.client_login"))

    client_id = session["client_id"]

    if request.method == "POST":
        label = request.form["label"]
        field_type = request.form["field_type"]
        category = request.form["category"]
        insert_field(client_id, label, field_type, category)
        # Log questionnaire field creation
        log_data_create('questionnaire_fields', client_id, {
            'label': label,
            'field_type': field_type,
            'category': category
        })
        return redirect(url_for("client_bp.client_questionnaire"))
    else:
        fields = get_fields_for_client(client_id)
        return render_template("client_questionnaire.html", fields=fields)


@client_bp.route("/delete_field/<int:field_id>", methods=["POST"])
def client_delete_field(field_id):
    """
    Delete a field from the client's questionnaire.
    """
    if "client_id" not in session:
        return redirect(url_for("client_bp.client_login"))

    client_id = session["client_id"]
    # Log field deletion before deleting
    log_data_delete('questionnaire_fields', field_id, {'client_id': client_id})
    delete_field(field_id, client_id)
    return redirect(url_for("client_bp.client_questionnaire"))
