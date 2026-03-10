from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from data.client_database import insert_client, find_client_by_username
from data.questionnaire_client import insert_field, get_fields_for_client, delete_field
import os

clients= Flask(
    __name__,
    template_folder="presentation/templates",
    static_folder="presentation/static"
)

clients.secret_key = os.getenv("CLIENT_APP_SECRET_KEY")

"""
Below is how clients are logged into the system
If a post request is recieved then use this data to check the user
and if all is correct log them in

If a get request is recieved then it redners the login page to the user
"""
@clients.route("/", methods=["GET", "POST"])
def client_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        client = find_client_by_username(username)
        if client and check_password_hash(client[2], password):
            session["client_id"] = client[0]
            session["client_username"] = client[1]
            return redirect(url_for("client_dashboard"))
        else:
            flash("Invalid username or password.")
            return render_template("client_login.html")
    else:
        return render_template("client_login.html")

"""
Resgiter works in the same way as the above.
If a post request is recieved insert the new user data
aslong as the username is unique

If a get request is recueved then show the user the register template
"""

@clients.route("/register", methods=["GET", "POST"])
def client_register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        dupliacte = find_client_by_username(username)
        if dupliacte:
            flash("Username already exists. Please choose another.")
            return render_template("client_register.html")


        password_hash = generate_password_hash(password)
        client_id = insert_client(username, password_hash)
        session["client_id"] = client_id
        session["client_username"] = username


        return redirect(url_for("client_dashboard"))
    else:
        return render_template("client_register.html")

"""
This logout function simply clears the session id
which will logout the user and redirect them to the login page
"""

@clients.route("/logout")
def client_logout():
    session.clear()
    return redirect(url_for("client_login"))


"""
Check the user is logged in, if they are not then return them to the login page
If they are logged in then show them the client dashboard
"""
@clients.route("/dashboard")
def client_dashboard():
    if "client_id" not in session:
        return redirect(url_for("client_login"))
    
    else:
        return render_template(
            "client_dashboard.html",
            username = session.get("client_username")
    )


"""
Ensure the user is logged in, set the client id for the session
If a post request is recieved then store the new fields the client 
has entered and insert them into the database

If a get request is recieved then display the questionnaire to the client
They can see the fields and categories of there proposed questionnaire
"""

@clients.route("/questionnaire", methods=["GET", "POST"])
def client_questionnaire():
 
    if "client_id" not in session:
        return redirect(url_for("client_login"))
    else:
        pass

    client_id = session["client_id"]

    if request.method == "POST":
        label = request.form["label"]
        field_type = request.form["field_type"]
        category = request.form["category"]
        insert_field(client_id, label, field_type, category)
        return redirect(url_for("client_questionnaire"))
    else:
        fields = get_fields_for_client(client_id)
        return render_template("client_questionnaire.html", fields=fields)


"""
This function deletes a field from a clients questionnaire
"""
@clients.route("/delete_field/<int:field_id>", methods=["POST"])
def client_delete_field(field_id):
    if "client_id" not in session:
        return redirect(url_for("client_login"))

    client_id = session["client_id"]
    delete_field(field_id, client_id)
    return redirect(url_for("client_questionnaire"))


if __name__ == "__main__":
    clients.run(debug=True, port=5001)
