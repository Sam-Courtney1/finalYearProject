from data.db_connection import get_db_connection

"""
This file holds functions to allow clients to create new fields in there questionnaries
The insert field takes the infomation from the client (client_id is stored in the session)
All other variables are passed in directly from the form
"""

def insert_field(client_id, label, field_type, category, is_required = True):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                INSERT INTO questionnaire_fields (client_id, field_label, field_type, category, is_required)
                VALUES (%s, %s, %s, %s, %s);
                """, (client_id, label, field_type, category, is_required))
    conn.commit()
    cur.close()
    conn.close()

"""
This returns all fields for a specifc client
Is used to display to the list of fields to the client 
when the client is editing the questionnaire
"""
def get_fields_for_client(client_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
                SELECT field_id, field_label, field_type, category
                FROM questionnaire_fields
                WHERE client_id = %s
                ORDER BY field_id;
                """, (client_id,))
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
