from data.db_connection import get_db_connection
from flask import session

"""
Inster a new client when they register
Return the newly made id and set it as the
sessions client_id

"""
def insert_client(username, password_hash):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO clients (username, password_hash)
        VALUES (%s, %s)
        RETURNING client_id; 
    """, (username, password_hash))
    # Need to index as its returned as a tuple (3,)
    # No index gives an error
    client_id = cur.fetchone()[0] 
    session['client_id'] = client_id
    conn.commit()
    cur.close()
    conn.close()
    return client_id

"""
Lookup any records in the client table under a certain username
Client id is used to set the id of the seesion upon login
Username is used to set the username of the seesion upon login
Password hash is used to compare to the user entered password
"""

def find_client_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT client_id, username, password_hash
        FROM clients
        WHERE username = %s; 
    """, (username,)) 
    client = cur.fetchone()
    cur.close()
    conn.close()
    return client
