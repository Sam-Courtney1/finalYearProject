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
        print("Migrations completed successfully")
        return True
    except Exception as e:
        print(f"Error running migrations: {e}")
        conn.close()
        return False
