from flask import Blueprint, render_template, session
from application.services.decorators import require_user_login

"""
__name__ is used to hold the name of the module it was created in
Eg in this file __name__ = application.routes.home_route
"""

home_bp = Blueprint('home_bp', __name__)


# Displays the homepage to the user only if the user is logged in
# If not then return the user to the login page to login
@home_bp.route('/homepage')
@require_user_login
def homepage():
    first_login = session.pop('first_login', False)
    return render_template('homepage.html', username=session['username'], first_login=first_login)
