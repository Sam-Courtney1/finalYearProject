from flask import Blueprint, render_template, request, redirect, url_for, session
from application.services.log_form_data import handle_questionnaire_submission

"""
questionnaire_bp is an object of Blueprint that stores its name (questionnaire_bp) 
The module where it is definined is inside of __name__
And all routes that belong to it
"""

questionnaire_bp = Blueprint('questionnaire_bp', __name__)


# Below are all the routes and actions that are assigned to questionnaire_bp
# These include displaying pages to users and allowing them to login and register

@questionnaire_bp.route('/questionnaire')
def questionnaire_form():
    return render_template('questionnaire.html')

@questionnaire_bp.route('/questionnaire', methods = ['POST'])
def submit_questionnaire():
    # If somehow the user gets to this page and is not logged in 
    # Then no use_id will be in session so return them to be logged in
    # Double security as users cannot type in the url extension to get to this page
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    handle_questionnaire_submission(session['user_id'], request.form)
    return redirect(url_for('home_bp.homepage'))
