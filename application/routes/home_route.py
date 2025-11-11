from flask import Blueprint, render_template, session, redirect, url_for

"""
home_bp is an object of Blueprint that stores its name (home_bp) 
The module where it is definined is inside of __name__
And all routes that belong to it

__name__ is used to hold the name of the module it was created in
Eg in this file __name__ = application.routes.home_route
"""

home_bp = Blueprint('home_bp', __name__)

# Displays the homepage to the user only if the user is logged in 
# If not then return the user to the login page to login

@home_bp.route('/homepage')
def homepage():
    if 'username' in session:
        return render_template('homepage.html', username = session['username'])
    else:
        return redirect(url_for('auth_bp.login_page'))

