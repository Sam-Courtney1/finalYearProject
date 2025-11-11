from data.db_connection import get_db_connection
import os

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


"""
The function below is used when a user requests to see there data
An sql request is made to return this data and tables are joined
on submissions.submission_id. This ensures that all user data is 
returned to the user and also ensures that onyl that users data is
shown and no one elses.
"""

def get_user_data(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # The key is used to decrypt from the database
    key = os.getenv("APP_ENC_KEY")

    cur.execute("""
        SELECT 
            u.username,
            s.consent,
            pgp_sym_decrypt(p.first_name_enc::bytea, %s) AS first_name,
            pgp_sym_decrypt(p.address_enc::bytea, %s) AS address,
            pgp_sym_decrypt(m.blood_type_enc::bytea, %s) AS blood_type,
            pgp_sym_decrypt(m.organ_enc::bytea, %s) AS organ,
            d.age
        FROM users u
        JOIN submissions s ON u.id = s.user_id
        LEFT JOIN pii p ON s.submission_id = p.submission_id
        LEFT JOIN medical_data m ON s.submission_id = m.submission_id
        LEFT JOIN demographic_data d ON s.submission_id = d.submission_id
        WHERE u.id = %s;
    """, (key, key, key, key, user_id))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

"""
This function takes the users id and make a query to delete the user
All records related to that user id are automatically deleted
"""
def delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
                delete from users where id = %s
                """, (user_id,))
    
    conn.commit()
    cur.close()
    conn.close()

