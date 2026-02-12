from data.db_connection import get_db_connection
import os

"""
Submission data operations for editing answers and managing consent.
Handles retrieving, updating, and consent withdrawal for questionnaire submissions.
"""


def get_user_submissions(user_id):
    """
    Returns all questionnaire submissions for a user (excludes the
    NULL-client registration submission). Used by both the edit selection
    page and the consent management page.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.submission_id, s.client_id, c.username, s.consent_withdrawn
        FROM submissions s
        JOIN clients c ON s.client_id = c.client_id
        WHERE s.user_id = %s AND s.client_id IS NOT NULL
        ORDER BY c.username;
    """, (user_id,))
    submissions = cur.fetchall()
    cur.close()
    conn.close()
    return submissions


def get_submission_answers(submission_id, user_id):
    """
    Decrypts and returns all answers for a submission, skipping Hashed fields.
    Verifies the submission belongs to the given user for security.
    Returns list of (field_id, field_label, field_type, category, current_value).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    key = os.getenv("APP_ENC_KEY")

    # Verify ownership
    cur.execute("""
        SELECT user_id, client_id FROM submissions WHERE submission_id = %s
    """, (submission_id,))
    row = cur.fetchone()
    if not row or row[0] != user_id:
        cur.close()
        conn.close()
        return None

    # Get all answers with field metadata, decrypting where needed
    # Hashed fields are excluded because they cannot be displayed
    cur.execute("""
        SELECT
            f.field_id,
            f.field_label,
            f.field_type,
            f.category,
            CASE
                WHEN f.category IN ('PII', 'Medical') THEN pgp_sym_decrypt(a.value::bytea, %s)::text
                ELSE a.value::text
            END AS current_value
        FROM answers a
        JOIN questionnaire_fields f ON a.field_id = f.field_id
        WHERE a.submission_id = %s
          AND f.category != 'Hashed'
        ORDER BY f.field_id;
    """, (key, submission_id))

    answers = cur.fetchall()
    cur.close()
    conn.close()
    return answers


def update_submission_answers(submission_id, user_id, updated_fields):
    """
    Updates answers for a submission with appropriate re-encryption.
    PII/Medical fields are re-encrypted with pgp_sym_encrypt.
    Hashed fields are skipped entirely.
    Plain text fields are stored as-is.

    Parameters:
        submission_id: int
        user_id: int (for ownership verification)
        updated_fields: dict of {field_id: new_value}

    Returns count of fields that were actually changed, or None if not owned.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    key = os.getenv("APP_ENC_KEY")

    # Verify ownership
    cur.execute("SELECT user_id FROM submissions WHERE submission_id = %s", (submission_id,))
    row = cur.fetchone()
    if not row or row[0] != user_id:
        cur.close()
        conn.close()
        return None

    changed_count = 0

    for field_id_str, new_value in updated_fields.items():
        field_id = int(field_id_str)

        # Get category for this field
        cur.execute("SELECT category FROM questionnaire_fields WHERE field_id = %s", (field_id,))
        result = cur.fetchone()
        if not result:
            continue
        category = result[0]

        # Skip hashed fields, they cannot be updated
        if category == "Hashed":
            continue

        # Get old value to check if it actually changed
        if category in ("PII", "Medical"):
            cur.execute("""
                SELECT pgp_sym_decrypt(value::bytea, %s)::text
                FROM answers
                WHERE submission_id = %s AND field_id = %s
            """, (key, submission_id, field_id))
        else:
            cur.execute("""
                SELECT value FROM answers
                WHERE submission_id = %s AND field_id = %s
            """, (submission_id, field_id))

        old_row = cur.fetchone()
        old_value = old_row[0] if old_row else None

        # Only update if value actually changed
        if old_value == new_value:
            continue

        # Update with appropriate encryption
        if category in ("PII", "Medical"):
            cur.execute("""
                UPDATE answers
                SET value = pgp_sym_encrypt(%s, %s)::text, updated_at = NOW()
                WHERE submission_id = %s AND field_id = %s
            """, (new_value, key, submission_id, field_id))
        else:
            cur.execute("""
                UPDATE answers
                SET value = %s, updated_at = NOW()
                WHERE submission_id = %s AND field_id = %s
            """, (new_value, submission_id, field_id))

        changed_count += 1

    conn.commit()
    cur.close()
    conn.close()
    return changed_count


def withdraw_consent(submission_id, user_id):
    """
    Withdraws consent for a specific submission.
    Sets consent_withdrawn=TRUE and records the timestamp.
    Returns True on success, False if not found or not owned.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE submissions
        SET consent_withdrawn = TRUE, consent_withdrawn_at = NOW()
        WHERE submission_id = %s AND user_id = %s
        RETURNING submission_id;
    """, (submission_id, user_id))

    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return result is not None


def reinstate_consent(submission_id, user_id):
    """
    Re-gives consent for a previously withdrawn submission.
    Clears the withdrawal flag and timestamp.
    Returns True on success, False if not found or not owned.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE submissions
        SET consent_withdrawn = FALSE, consent_withdrawn_at = NULL
        WHERE submission_id = %s AND user_id = %s
        RETURNING submission_id;
    """, (submission_id, user_id))

    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return result is not None
