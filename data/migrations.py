from data.db_connection import get_db_connection

"""
Database migrations for schema changes.
Called during application startup to ensure the schema is up to date.
Each migration uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
so it is safe to run multiple times.
"""


def run_migrations():
    conn = get_db_connection()
    if conn is None:
        print("Migration skipped: no database connection")
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

        print("Migrations completed successfully")
        return True
    except Exception as e:
        print(f"Error running migrations: {e}")
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
        print("Deletion tracking migration completed")
        return True
    except Exception as e:
        print(f"Error in deletion tracking migration: {e}")
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

        # Add questionnaire_name column (nullable initially for migration)
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
        print("Questionnaire names migration completed")
        return True
    except Exception as e:
        print(f"Error in questionnaire names migration: {e}")
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
        print("Submissions questionnaire tracking migration completed")
        return True
    except Exception as e:
        print(f"Error in submissions questionnaire tracking migration: {e}")
        conn.close()
        return False
