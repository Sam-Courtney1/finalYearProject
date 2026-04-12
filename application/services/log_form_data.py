from data.db_connection import get_db
from werkzeug.security import generate_password_hash
import os

"""
The below function takes in static and dynamic fields when a questionnaire is submitted
It creates a submissions record with the user and client as well as if the user gave there consent
submissions_id is returned straight away as this is needed in all the inserts later on

Submision_id is added into pii aswell as first name and addess which are both enncrypted

Submissoin_id and age are put into the demographic_data table as plain text
"""


def handle_questionnaire_submission(user_id, client_id, questionnaire_name, form_data):
    """ Handles questionnaire submission with questionnaire_name parameter. """
    with get_db() as (conn, cur):
        # Enforce is_required: check all required fields are present and non-empty
        cur.execute("""
                    SELECT field_id, field_label FROM questionnaire_fields
                    WHERE client_id = %s AND questionnaire_name = %s AND is_required = TRUE;
                    """, (client_id, questionnaire_name))
        required_fields = cur.fetchall()

        missing = []
        for field_id, field_label in required_fields:
            form_key = f"field_{field_id}"
            if form_key not in form_data or not form_data[form_key].strip():
                missing.append(field_label)

        if missing:
            raise ValueError(f"Required fields missing: {', '.join(missing)}")

        cur.execute("""
                    INSERT INTO submissions (user_id, client_id, questionnaire_name)
                    VALUES (%s, %s, %s)
                    RETURNING submission_id;
                    """, (user_id, client_id, questionnaire_name))

        submission_id = cur.fetchone()[0]
        key = os.getenv("APP_ENC_KEY")

        """
        This for loop goes through client made fields and goes through the key pai values
        Ie the name of the field and the value entered by the user
        All new variables start with field, all static variables dont ie age , name etc
        """
        for key_name, value in form_data.items():
            if not key_name.startswith("field_"):
                continue
            field_id = int(key_name.split("_")[1])

            # Check each category to determine if the data needs to be encrypted, hashed or left as plain text
            # The logic below determines the form of secuirty applied based on this category
            cur.execute("SELECT category FROM questionnaire_fields WHERE field_id = %s", (field_id,))
            category = cur.fetchone()[0]

            if category in ("PII", "Medical"):
                cur.execute("""
                            INSERT INTO answers (submission_id, field_id, value)
                            VALUES (%s, %s, pgp_sym_encrypt(%s, %s)::text);
                            """, (submission_id, field_id, value, key))
            elif category == "Hashed":
                hashed_val = generate_password_hash(value)
                cur.execute("""
                            INSERT INTO answers (submission_id, field_id, value)
                            VALUES (%s, %s, %s);
                            """, (submission_id, field_id, hashed_val))
            else:
                cur.execute("""
                            INSERT INTO answers (submission_id, field_id, value)
                            VALUES (%s, %s, %s);
                            """, (submission_id, field_id, value))
