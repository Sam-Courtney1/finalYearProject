from data.db_connection import get_db_connection

"""
This file returns information about a user based on there username
It is used for loggin into the styem

The second function in this file is used to insert a user into
the database
"""

def find_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def insert_user(username, hashed_password):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
    conn.commit()
    cur.close()
    conn.close()
