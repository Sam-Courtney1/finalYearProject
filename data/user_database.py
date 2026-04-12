from data.db_connection import get_db
import hashlib
import os

# This file returns information about a user based on there username
# It is used for loggin into the system
#
# This file contains all database operations concerning the end user (data subject)


def find_by_username(username):
    with get_db() as (conn, cur):
        cur.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        return cur.fetchone()


def find_by_id(user_id):
    with get_db() as (conn, cur):
        cur.execute("SELECT id, password FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()


def insert_user(username, hashed_password):
    with get_db() as (conn, cur):
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))


def create_user_profile(user_id, username, email, address, age):
    """
    Create the initial user profile after registration.
    Stores encrypted email, creates a base submission, and inserts PII + demographics.
    Shared by both the web register route and the mobile API register route.
    """
    key = os.getenv("APP_ENC_KEY")
    with get_db() as (conn, cur):
        cur.execute("""
            UPDATE users SET email_enc = pgp_sym_encrypt(%s, %s) WHERE id = %s;
        """, (email, key, user_id))

        cur.execute("""
            INSERT INTO submissions (user_id, client_id)
            VALUES (%s, NULL) RETURNING submission_id;
        """, (user_id,))
        submission_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO pii (submission_id, first_name_enc, address_enc)
            VALUES (%s, pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s));
        """, (submission_id, username, key, address, key))

        cur.execute("""
            INSERT INTO demographic_data (submission_id, age)
            VALUES (%s, %s);
        """, (submission_id, age))


def update_last_login(user_id):
    """Update the last_login timestamp for data retention tracking."""
    with get_db() as (conn, cur):
        cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))


def get_user_data(user_id):
    with get_db() as (conn, cur):
        # The key is used to decrypt from the database
        key = os.getenv("APP_ENC_KEY")

        cur.execute("""
            SELECT
                pgp_sym_decrypt(p.first_name_enc::bytea, %s) AS first_name,
                pgp_sym_decrypt(p.address_enc::bytea, %s) AS address,
                d.age
            FROM users u
            JOIN submissions s ON u.id = s.user_id
            LEFT JOIN pii p ON s.submission_id = p.submission_id
            LEFT JOIN demographic_data d ON s.submission_id = d.submission_id
            WHERE u.id = %s
                    AND s.client_id IS NULL;
        """, (key, key, user_id))
        # Static fields are the fields which are always used ie age , name and address
        static_data = cur.fetchall()

        # Gather all of the data from the fields that the client has added
        # Joins all tables and returns based on the user_id so that only
        # the data related to that user is returned
        #
        # ::text is needed as to change the binary data into letters
        #
        # The CASE acts as an if statment and only decrypts data if it is
        # encrypted in the first place
        cur.execute("""
            SELECT
                c.username AS company_name,
                f.field_label,
                f.category,
                CASE
                    WHEN f.category IN ('PII', 'Medical') THEN pgp_sym_decrypt(a.value::bytea, %s)::text
                    ELSE a.value::text
                END AS value,
                s.consent_withdrawn,
                s.submission_id
            FROM answers a
            JOIN questionnaire_fields f ON a.field_id = f.field_id
            JOIN submissions s ON a.submission_id = s.submission_id
            JOIN clients c ON s.client_id = c.client_id
            WHERE s.user_id = %s;
        """, (key, user_id))

        # Fetch all rows from the result and store them
        dynamic_data = cur.fetchall()

        return static_data, dynamic_data


def delete_user(user_id):
    with get_db() as (conn, cur):
        # Anonymize audit logs before deleting the user (GDPR Art. 17 + audit integrity).
        # Replace actor_id with NULL and store a SHA-256 hash prefix in details
        # so logs can still be correlated without identifying the user.
        hash_prefix = hashlib.sha256(str(user_id).encode()).hexdigest()[:12]
        cur.execute("""
            UPDATE audit_logs
            SET details = jsonb_set(
                COALESCE(details, '{}'::jsonb),
                '{anonymised_actor}', to_jsonb(%s::text)
            ),
            actor_id = NULL
            WHERE actor_id = %s AND actor_type = 'user';
        """, (f"deleted_{hash_prefix}", user_id))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))


def get_user_data_for_client(client_id):
    """
    Returns questionnaire data for a specific client, but only where
    consent has not been withdrawn. This is the function any future
    client facing data view must use to respect consent withdrawal.
    """
    with get_db() as (conn, cur):
        key = os.getenv("APP_ENC_KEY")

        cur.execute("""
            SELECT
                f.field_label,
                f.category,
                CASE
                    WHEN f.category IN ('PII', 'Medical') THEN pgp_sym_decrypt(a.value::bytea, %s)::text
                    ELSE a.value::text
                END AS value,
                s.user_id,
                s.submission_id
            FROM answers a
            JOIN questionnaire_fields f ON a.field_id = f.field_id
            JOIN submissions s ON a.submission_id = s.submission_id
            WHERE s.client_id = %s
              AND s.consent_withdrawn = FALSE;
        """, (key, client_id))

        return cur.fetchall()


def delete_user_data_only(user_id):
    """
    Delete all stored data but not the users account
    """
    with get_db() as (conn, cur):
        # Deleting submissions will cascade to pii, demographic_data, answers, etc.
        cur.execute("""
            DELETE FROM submissions
            WHERE user_id = %s;
        """, (user_id,))
