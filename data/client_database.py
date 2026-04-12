from data.db_connection import get_db


# Insert a new client and return there ID to be set in the session
def insert_client(username, password_hash):
    with get_db() as (conn, cur):
        cur.execute("""
            INSERT INTO clients (username, password_hash)
            VALUES (%s, %s)
            RETURNING client_id;
        """, (username, password_hash))
        # Below needs to be indexed as
        # the data being returned is a tuple ie ( 42 , )
        client_id = cur.fetchone()[0]
        return client_id


"""
Lookup any records in the client table under a certain username
Client id is used to set the id of the seesion upon login
Username is used to set the username of the seesion upon login
Password hash is used to compare to the user entered password
"""


def find_client_by_username(username):
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT client_id, username, password_hash
            FROM clients
            WHERE username = %s;
        """, (username,))
        return cur.fetchone()
