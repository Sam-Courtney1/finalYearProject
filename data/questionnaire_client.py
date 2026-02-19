from data.db_connection import get_db_connection

"""
This file holds functions to allow clients to create new fields in there questionnaries
The insert field takes the infomation from the client (client_id is stored in the session)
All other variables are passed in directly from the form
"""

def insert_field(client_id, questionnaire_name, label, field_type, category, is_required = True):
    """
    Insert a new field into a specific questionnaire for a client.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO questionnaire_fields (client_id, questionnaire_name, field_label, field_type, category, is_required)
                VALUES (%s, %s, %s, %s, %s, %s);
                """, (client_id, questionnaire_name, label, field_type, category, is_required))
    conn.commit()
    cur.close()
    conn.close()

"""
This returns all fields for a specifc client's specific questionnaire
Is used to display to the list of fields to the client
when the client is editing the questionnaire
"""
def get_fields_for_client(client_id, questionnaire_name):
    """
    Returns all fields for a specific client's specific questionnaire.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                SELECT field_id, field_label, field_type, category
                FROM questionnaire_fields
                WHERE client_id = %s AND questionnaire_name = %s
                ORDER BY field_id;
                """, (client_id, questionnaire_name))
    fields = cur.fetchall()
    cur.close()
    conn.close()
    return fields

"""
Deletes a custom field from a specific client
"""
def delete_field(field_id, client_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                DELETE FROM questionnaire_fields
                WHERE field_id = %s AND client_id = %s;
                """, (field_id, client_id))
    conn.commit()
    cur.close()
    conn.close()


def get_questionnaires_for_client(client_id):
    """
    Returns all distinct questionnaire names for a client with field counts
    and active submission counts.

    This is used to show a client what there questionares are called and
    how many users have filled them out
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                SELECT
                    qf.questionnaire_name,
                    COUNT(DISTINCT qf.field_id) as field_count,
                    COALESCE(sub_counts.submission_count, 0) as submission_count
                FROM questionnaire_fields qf
                LEFT JOIN (
                    SELECT questionnaire_name, COUNT(*) as submission_count
                    FROM submissions
                    WHERE client_id = %s
                      AND consent_withdrawn = FALSE
                      AND deleted = FALSE
                    GROUP BY questionnaire_name
                ) sub_counts ON qf.questionnaire_name = sub_counts.questionnaire_name
                WHERE qf.client_id = %s
                GROUP BY qf.questionnaire_name, sub_counts.submission_count
                ORDER BY qf.questionnaire_name;
                """, (client_id, client_id))
    questionnaires = cur.fetchall()
    cur.close()
    conn.close()
    return questionnaires


def questionnaire_name_exists(client_id, questionnaire_name):
    """
    Check if a questionnaire name already exists for a client.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                SELECT COUNT(*) FROM questionnaire_fields
                WHERE client_id = %s AND questionnaire_name = %s;
                """, (client_id, questionnaire_name))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    # Returns true or false
    return count > 0
