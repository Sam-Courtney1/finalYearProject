from data.db_connection import get_db
import os

"""
Submission data operations for editing answers and managing consent.
Handles retrieving, updating, and consent withdrawal for questionnaire submissions.
"""


def _rows_to_dicts(cur, rows):
    """Convert database rows to a list of dicts using cursor column names."""
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def get_user_submissions(user_id):
    """
    Returns all questionnaire submissions for a user
    Used by both the edit selection page and the consent management page.
    """
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT s.submission_id, s.client_id, c.username, s.consent_withdrawn, s.questionnaire_name
            FROM submissions s
            JOIN clients c ON s.client_id = c.client_id
            WHERE s.user_id = %s
                AND s.client_id IS NOT NULL
                AND s.deleted = FALSE
            ORDER BY c.username, s.questionnaire_name;
        """, (user_id,))
        return cur.fetchall()


def get_submission_answers(submission_id, user_id):
    """
    Decrypts and returns all answers for a submission, skipping Hashed fields.
    Verifies the submission belongs to the given user for security.
    """
    with get_db() as (conn, cur):
        key = os.getenv("APP_ENC_KEY")

        # Verify ownership
        cur.execute("""
            SELECT user_id, client_id FROM submissions WHERE submission_id = %s
        """, (submission_id,))
        row = cur.fetchone()
        if not row or row[0] != user_id:
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

        return cur.fetchall()


def update_submission_answers(submission_id, user_id, updated_fields):
    """
    Updates answers for a submission with appropriate re encryption.
    PII/Medical fields are re encrypted with pgp_sym_encrypt.
    Hashed fields are skipped entirely.
    Plain text fields are stored as is.

    Returns count of fields that were actually changed, or None if not owned.
    """
    with get_db() as (conn, cur):
        key = os.getenv("APP_ENC_KEY")

        # Verify ownership
        cur.execute("SELECT user_id FROM submissions WHERE submission_id = %s", (submission_id,))
        row = cur.fetchone()
        if not row or row[0] != user_id:
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

        return changed_count


def get_submissions_for_questionnaire(client_id, questionnaire_name):
    """
    Returns anonymised submission data for a specific questionnaire.
    Excludes Hashed fields, respects consent withdrawal and soft deletion.
    User identities are replaced with Respondent 1, Respondent 2, etc.
    """

    with get_db() as (conn, cur):
        key = os.getenv("APP_ENC_KEY")

        cur.execute("""
            SELECT
                s.submission_id,
                f.field_label,
                f.field_id,
                CASE
                    WHEN f.category IN ('PII', 'Medical') THEN pgp_sym_decrypt(a.value::bytea, %s)::text
                    ELSE a.value::text
                END AS value
            FROM answers a
            JOIN questionnaire_fields f ON a.field_id = f.field_id
            JOIN submissions s ON a.submission_id = s.submission_id
            WHERE s.client_id = %s
              AND s.questionnaire_name = %s
              AND s.consent_withdrawn = FALSE
              AND s.deleted = FALSE
              AND f.category != 'Hashed'
            ORDER BY s.submission_id, f.field_id;
        """, (key, client_id, questionnaire_name))

        rows = cur.fetchall()

    if not rows:
        return [], []

    # Build column headers from field labels
    seen_fields = {}
    column_headers = []
    for row in rows:
        field_id = row[2]
        field_label = row[1]
        if field_id not in seen_fields:
            seen_fields[field_id] = field_label
            column_headers.append(field_label)

    # assign sequential Respondent N labels per submission_id
    submission_map = {}
    submission_order = []
    respondent_counter = 0

    for row in rows:
        submission_id = row[0]
        field_label = row[1]
        value = row[3]

        if submission_id not in submission_map:
            respondent_counter += 1
            submission_map[submission_id] = {
                'respondent_label': f"Respondent {respondent_counter}",
                'answers': {}
            }
            submission_order.append(submission_id)

        submission_map[submission_id]['answers'][field_label] = value

    submissions_data = [submission_map[sid] for sid in submission_order]
    return column_headers, submissions_data


def withdraw_consent(submission_id, user_id):
    """
    Withdraws consent for a specific submission.
    Sets consent_withdrawn=TRUE and records the timestamp.
    Returns True on success, False if not found or not owned.
    """
    with get_db() as (conn, cur):
        cur.execute("""
            UPDATE submissions
            SET consent_withdrawn = TRUE, consent_withdrawn_at = NOW()
            WHERE submission_id = %s AND user_id = %s
            RETURNING submission_id;
        """, (submission_id, user_id))

        result = cur.fetchone()
        return result is not None


def reinstate_consent(submission_id, user_id):
    """
    Re gives consent for a previously withdrawn submission.
    Clears the withdrawal flag and timestamp.
    Returns True on success, False if not found or not owned.
    """
    with get_db() as (conn, cur):
        cur.execute("""
            UPDATE submissions
            SET consent_withdrawn = FALSE, consent_withdrawn_at = NULL
            WHERE submission_id = %s AND user_id = %s
            RETURNING submission_id;
        """, (submission_id, user_id))

        result = cur.fetchone()
        return result is not None


def delete_single_submission(submission_id, user_id):
    """
    Deletes a single submission and all related data.
    Uses soft deletion for the submission record (audit trail) and hard deletion for answers/PII.
    """
    with get_db() as (conn, cur):
        # Verify ownership and get client info
        cur.execute("""
            SELECT s.user_id, c.username
            FROM submissions s
            JOIN clients c ON s.client_id = c.client_id
            WHERE s.submission_id = %s AND s.deleted = FALSE
        """, (submission_id,))

        row = cur.fetchone()
        if not row or row[0] != user_id:
            return None

        client_name = row[1]

        # Count answers before deletion (for logging)
        cur.execute("""
            SELECT COUNT(*) FROM answers WHERE submission_id = %s
        """, (submission_id,))
        answers_count = cur.fetchone()[0]

        # Hard delete answers (CASCADE will handle pii, demographic_data)
        cur.execute("""
            DELETE FROM answers WHERE submission_id = %s
        """, (submission_id,))

        # Soft delete the submission (preserve for audit trail)
        cur.execute("""
            UPDATE submissions
            SET deleted = TRUE,
                deleted_at = NOW(),
                deletion_reason = 'user_requested_single_submission'
            WHERE submission_id = %s
        """, (submission_id,))

        return {
            'success': True,
            'client_name': client_name,
            'answers_deleted': answers_count
        }


def get_user_dashboard_stats(user_id):
    """
    Returns dashboard statistics for a user
    Total submissions count
    List of organisations with submission details and consent status
    """

    with get_db() as (conn, cur):
        cur.execute("""
            SELECT s.submission_id, c.username AS org_name, s.questionnaire_name,
                   s.consent_withdrawn, s.created_at
            FROM submissions s
            JOIN clients c ON s.client_id = c.client_id
            WHERE s.user_id = %s
              AND s.client_id IS NOT NULL
              AND s.deleted = FALSE
            ORDER BY s.created_at DESC;
        """, (user_id,))
        submissions = _rows_to_dicts(cur, cur.fetchall())

        # Aggregate stats
        total = len(submissions)
        orgs = set(s['org_name'] for s in submissions)
        active_consents = sum(1 for s in submissions if not s['consent_withdrawn'])
        withdrawn_consents = sum(1 for s in submissions if s['consent_withdrawn'])

        return {
            'total_submissions': total,
            'total_organisations': len(orgs),
            'active_consents': active_consents,
            'withdrawn_consents': withdrawn_consents,
            'submissions': submissions
        }
