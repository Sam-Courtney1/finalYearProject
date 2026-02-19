from data.db_connection import get_db_connection
import os

"""
This file takes data from the questionnaire
It connects to the database and inserts data into the correct tables

For sensitive data, encryption is used before being submitted
In this way all data is entered into the database in accordance
with GDPR security measures.
"""

def insert_questionnaire(user_id, first_name, age, address, blood_type, organ, consent):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
                INSERT INTO submissions (user_id, consent)
                VALUES (%s, %s)
                RETURNING submission_id;
                """, 

                (user_id, consent))
    # Indexed as data is returned as a tuple
    submission_id = cur.fetchone()[0]

    cur.execute("""
                INSERT INTO pii (submission_id, first_name_enc, address_enc)
                VALUES (%s, pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s));
                """,
                (submission_id, first_name, os.getenv("APP_ENC_KEY"), address, os.getenv("APP_ENC_KEY"))) 

    cur.execute("""
                INSERT INTO medical_data (submission_id, blood_type_enc, organ_enc)
                VALUES (%s, pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s));
                """, 
                (submission_id, blood_type, os.getenv("APP_ENC_KEY"), organ, os.getenv("APP_ENC_KEY")))
    cur.execute("""
                INSERT INTO demographic_data (submission_id, age)
                VALUES (%s, %s);
                """, 
                (submission_id, age))


    conn.commit()
    cur.close()
    conn.close()


