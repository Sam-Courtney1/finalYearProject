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
            d.age
        FROM users u
        JOIN submissions s ON u.id = s.user_id
        LEFT JOIN pii p ON s.submission_id = p.submission_id
        LEFT JOIN demographic_data d ON s.submission_id = d.submission_id
        WHERE u.id = %s;
    """, (key, key, user_id))
    # Static fields are the fields which are always used ie age , name and address
    static_data = cur.fetchall()

    """
    Gather all of the data from the fields that the client has added
    Joins all tables and returns based on the user_id so that only
    the data related to that user is returned

    ::text is needed as to change the binary data into letters
    """
    cur.execute("""
        SELECT 
            c.username AS company_name,
            f.field_label,
            f.category,
            CASE 
                WHEN f.category IN ('PII', 'Medical') THEN pgp_sym_decrypt(a.value::bytea, %s)::text
                ELSE a.value::text
            END AS value
        FROM answers a
        JOIN questionnaire_fields f ON a.field_id = f.field_id
        JOIN submissions s ON a.submission_id = s.submission_id
        JOIN clients c ON s.client_id = c.client_id
        WHERE s.user_id = %s;
    """, (key, user_id))

    # Fetch all rows from the result and store them 
    dynamic_data = cur.fetchall()

    cur.close()
    conn.close()
    return static_data, dynamic_data

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

