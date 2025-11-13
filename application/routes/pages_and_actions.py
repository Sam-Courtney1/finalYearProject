from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from application.services.authentication import register_user, authenticate_user
from data.user_database import find_by_username, get_user_data, delete_user

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
    return render_template('login.html')

@auth_bp.route('/register')
def register_page():
    return render_template('register.html')

@auth_bp.route('/register_user', methods = ['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    # Check to see if username already exists
    existing_user = find_by_username(username)
    if existing_user:
        flash("Username already exists. Please choose another.")
        return redirect(url_for('auth_bp.register_page'))
    else:
        pass
    

    # The register_user function inserts a user into the database
    register_user(username, password)
    session['username'] = username
    # make a second call to get the id. This is needed for entries
    # to be accteped into the database throught the questionnaire
    user = find_by_username(username)
    if user:
        session['user_id'] = user[0]
        return redirect(url_for('home_bp.homepage')) 
    else:
        return redirect(url_for('auth_bp.login_page')) 

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
        return redirect(url_for('home_bp.homepage'))
    else:
        return redirect(url_for('auth_bp.login_page'))

@auth_bp.route('/logout')
def logout():
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
def right_to_access():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        user_id = session['user_id']
    
    static_data, dynamic_data = get_user_data(user_id)
    return render_template('access_data.html', static_data = static_data, dynamic_data = dynamic_data)



@pages_bp.route('/right_to_forget', methods = ['POST'])
def right_to_forget():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login_page'))
    else:
        user_id = session['user_id']

    delete_user(user_id)
    session.clear()
    return redirect(url_for('auth_bp.login_page'))

