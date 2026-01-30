from werkzeug.security import generate_password_hash, check_password_hash
from data.user_database import find_by_username, insert_user

"""
The first function register's a user and hash's there passowrd
This ensures that all passwords are hashed as they are instered into the database 

The second function is used to authenticate the user upon logging into the system
The find_by_username function returns the user id and password
If the user varible has data inside of it ie there has been a successful return of data
from the function call and the password returned from the database matches the password
the user has entered, the user_id is returned and in another file is set as the current session_id
"""

def register_user(username, password):
    hashed = generate_password_hash(password)
    insert_user(username, hashed)

def authenticate_user(username, password):
    user = find_by_username(username)
    if user and check_password_hash(user[1], password):
        # Return user_id as this is the first argument returned from the fuction
        return user[0]  
    else:
        return None
