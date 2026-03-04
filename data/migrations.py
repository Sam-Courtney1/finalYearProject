from data.db_connection import get_db_connection
import logging

logger = logging.getLogger(__name__)

"""
Database migrations for schema changes.
Called during application startup to ensure the schema is up to date.
Each migration uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
so it is safe to run multiple times.
"""


def run_migrations():
    conn = get_db_connection()
    if conn is None:
        logger.warning("Migration skipped: no database connection")
        return False

    try:
        cur = conn.cursor()

        # Add consent withdrawal tracking to submissions table
        cur.execute("""
            ALTER TABLE submissions
                ADD COLUMN IF NOT EXISTS consent_withdrawn BOOLEAN NOT NULL DEFAULT FALSE;
        """)
        cur.execute("""
            ALTER TABLE submissions
                ADD COLUMN IF NOT EXISTS consent_withdrawn_at TIMESTAMPTZ DEFAULT NULL;
        """)

        # Add updated_at timestamp to answers table for tracking edits
        cur.execute("""
            ALTER TABLE answers
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NULL;
        """)

        conn.commit()
        cur.close()
        conn.close()

        # Run additional migrations
        add_deletion_tracking()
        add_questionnaire_names()
        add_questionnaire_tracking_to_submissions()
        add_2fa_and_email()

        logger.info("Migrations completed successfully")
        return True
    except Exception as e:
        logger.error("Error running migrations: %s", e)
        conn.rollback()
        conn.close()
        return False


def add_deletion_tracking():
    """
    Add deletion tracking columns to submissions table.
    Allows soft deletion of individual submissions while preserving audit trail.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()

        # Add deleted flag
        cur.execute("""
            ALTER TABLE submissions
                ADD COLUMN IF NOT EXISTS deleted BOOLEAN NOT NULL DEFAULT FALSE;
        """)

        # Add deletion timestamp
        cur.execute("""
            ALTER TABLE submissions
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
        """)

        # Add deletion reason
        cur.execute("""
            ALTER TABLE submissions
                ADD COLUMN IF NOT EXISTS deletion_reason TEXT DEFAULT NULL;
        """)

        # Add index for efficient queries excluding deleted submissions
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_submissions_not_deleted
                ON submissions(user_id) WHERE deleted = FALSE;
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Deletion tracking migration completed")
        return True
    except Exception as e:
        logger.error("Error in deletion tracking migration: %s", e)
        conn.rollback()
        conn.close()
        return False


def add_questionnaire_names():
    """
    Add questionnaire_name column to questionnaire_fields table.
    Allows organizations to create multiple distinct questionnaires.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()

        # Add questionnaire_name column
        cur.execute("""
            ALTER TABLE questionnaire_fields
                ADD COLUMN IF NOT EXISTS questionnaire_name VARCHAR(255);
        """)

        # Set default name for existing fields (per client)
        # Group existing fields under "Main Questionnaire" for each client
        cur.execute("""
            UPDATE questionnaire_fields
            SET questionnaire_name = 'Main Questionnaire'
            WHERE questionnaire_name IS NULL;
        """)

        # Now make it NOT NULL with default
        cur.execute("""
            ALTER TABLE questionnaire_fields
                ALTER COLUMN questionnaire_name SET NOT NULL,
                ALTER COLUMN questionnaire_name SET DEFAULT 'Main Questionnaire';
        """)

        # Add composite index for efficient queries by client_id + questionnaire_name
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_questionnaire_fields_client_qname
                ON questionnaire_fields(client_id, questionnaire_name);
        """)

        # Add unique constraint to prevent duplicate field labels within same questionnaire
        # Format: client_id + questionnaire_name + field_label must be unique
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_field_per_questionnaire
                ON questionnaire_fields(client_id, questionnaire_name, field_label);
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Questionnaire names migration completed")
        return True
    except Exception as e:
        logger.error("Error in questionnaire names migration: %s", e)
        conn.rollback()
        conn.close()
        return False


def add_2fa_and_email():
    """
    Add email storage to users table and create OTP/password-reset token tables.
    Supports email-based 2FA and password reset via AWS SES.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()

        # Add encrypted email column to users table
        cur.execute("""
            ALTER TABLE users
                ADD COLUMN IF NOT EXISTS email_enc BYTEA;
        """)

        # OTP tokens for 2FA - one active token per user at a time
        cur.execute("""
            CREATE TABLE IF NOT EXISTS otp_tokens (
                id           SERIAL PRIMARY KEY,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash   VARCHAR(64) NOT NULL,
                expires_at   TIMESTAMPTZ NOT NULL,
                used         BOOLEAN NOT NULL DEFAULT FALSE,
                attempts     INTEGER NOT NULL DEFAULT 0,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

        # Password reset tokens - one active token per user at a time
        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id           SERIAL PRIMARY KEY,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash   VARCHAR(64) NOT NULL,
                expires_at   TIMESTAMPTZ NOT NULL,
                used         BOOLEAN NOT NULL DEFAULT FALSE,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("2FA and email migration completed")
        return True
    except Exception as e:
        logger.error("Error in 2FA/email migration: %s", e)
        conn.rollback()
        conn.close()
        return False


def add_questionnaire_tracking_to_submissions():
    """
    Add questionnaire_name to submissions table to track which specific
    questionnaire the submission is for.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()

        # Add questionnaire_name column to submissions
        cur.execute("""
            ALTER TABLE submissions
                ADD COLUMN IF NOT EXISTS questionnaire_name VARCHAR(255);
        """)

        # Set default for existing submissions
        cur.execute("""
            UPDATE submissions
            SET questionnaire_name = 'Main Questionnaire'
            WHERE questionnaire_name IS NULL AND client_id IS NOT NULL;
        """)

        # Add index for efficient queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_submissions_client_qname
                ON submissions(client_id, questionnaire_name);
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Submissions questionnaire tracking migration completed")
        return True
    except Exception as e:
        logger.error("Error in submissions questionnaire tracking migration: %s", e)
        conn.rollback()
        conn.close()
        return False
