from data.db_connection import get_db

# This file holds functions to allow clients to create new fields in their questionnaries
# The insert field takes the infomation from the client (client_id is stored in the session)
# All other variables are passed in directly from the form


def insert_field(client_id, questionnaire_name, label, field_type, category, is_required=True):
    """
    Insert a new field into a specific questionnaire for a client.
    """
    with get_db() as (conn, cur):
        cur.execute("""
                    INSERT INTO questionnaire_fields
                    (client_id, questionnaire_name, field_label, field_type, category, is_required)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """, (client_id, questionnaire_name, label, field_type, category, is_required))


# This returns all fields for a specifc client's specific questionnaire
# Is used to display to the list of fields to the client
# when the client is editing the questionnaire


def get_fields_for_client(client_id, questionnaire_name):
    """
    Returns all fields for a specific client's specific questionnaire.
    """
    with get_db() as (conn, cur):
        cur.execute("""
                    SELECT field_id, field_label, field_type, category
                    FROM questionnaire_fields
                    WHERE client_id = %s AND questionnaire_name = %s
                    ORDER BY field_id;
                    """, (client_id, questionnaire_name))
        return cur.fetchall()


# Deletes a custom field from a specific client


def delete_field(field_id, client_id):
    with get_db() as (conn, cur):
        cur.execute("""
                    DELETE FROM questionnaire_fields
                    WHERE field_id = %s AND client_id = %s;
                    """, (field_id, client_id))


def get_questionnaires_for_client(client_id):
    """
    Returns all distinct questionnaire names for a client with field counts
    and active submission counts.

    This is used to show a client what there questionares are called and
    how many users have filled them out
    """
    with get_db() as (conn, cur):
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
        return cur.fetchall()


def questionnaire_name_exists(client_id, questionnaire_name):
    """
    Check if a questionnaire name already exists for a client.
    """
    with get_db() as (conn, cur):
        cur.execute("""
                    SELECT COUNT(*) FROM questionnaire_fields
                    WHERE client_id = %s AND questionnaire_name = %s;
                    """, (client_id, questionnaire_name))
        count = cur.fetchone()[0]
        # Returns true or false
        return count > 0
