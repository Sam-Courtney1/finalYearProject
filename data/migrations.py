"""
This file is no longer needed. It opens up to many connections and as i have set the max to 10 it will cause
errors and the pool of connections will be fully used.

It is being kept for use in my report
"""


def run_migrations():
    """No-op stub, migrations are disabled. See docstring above."""
    pass


# from data.db_connection import get_db_connection
# import logging

# logger = logging.getLogger(__name__)

# """
# Database migrations for schema changes.
# Called during application startup to ensure the schema is up to date.
# Each migration uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
# so it is safe to run multiple times.
# """


# def run_migrations():
#     conn = get_db_connection()
#     if conn is None:
#         logger.warning("Migration skipped: no database connection")
#         return False

#     try:
#         cur = conn.cursor()

#         # Add consent withdrawal tracking to submissions table
#         cur.execute("""
#             ALTER TABLE submissions
#                 ADD COLUMN IF NOT EXISTS consent_withdrawn BOOLEAN NOT NULL DEFAULT FALSE;
#         """)
#         cur.execute("""
#             ALTER TABLE submissions
#                 ADD COLUMN IF NOT EXISTS consent_withdrawn_at TIMESTAMPTZ DEFAULT NULL;
#         """)

#         # Add updated_at timestamp to answers table for tracking edits
#         cur.execute("""
#             ALTER TABLE answers
#                 ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NULL;
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()

#         # Run additional migrations
#         add_deletion_tracking()
#         add_questionnaire_names()
#         add_questionnaire_tracking_to_submissions()
#         add_2fa_and_email()
#         add_audit_client_id()
#         add_auditors_table()
#         add_last_login_column()
#         add_data_breaches_table()
#         add_dsr_table()
#         add_breach_notifications_table()

#         logger.info("Migrations completed successfully")
#         return True
#     except Exception as e:
#         logger.error("Error running migrations: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_deletion_tracking():
#     """
#     Add deletion tracking columns to submissions table.
#     Allows soft deletion of individual submissions while preserving audit trail.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         # Add deleted flag
#         cur.execute("""
#             ALTER TABLE submissions
#                 ADD COLUMN IF NOT EXISTS deleted BOOLEAN NOT NULL DEFAULT FALSE;
#         """)

#         # Add deletion timestamp
#         cur.execute("""
#             ALTER TABLE submissions
#                 ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
#         """)

#         # Add deletion reason
#         cur.execute("""
#             ALTER TABLE submissions
#                 ADD COLUMN IF NOT EXISTS deletion_reason TEXT DEFAULT NULL;
#         """)

#         # Add index for efficient queries excluding deleted submissions
#         cur.execute("""
#             CREATE INDEX IF NOT EXISTS idx_submissions_not_deleted
#                 ON submissions(user_id) WHERE deleted = FALSE;
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Deletion tracking migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in deletion tracking migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_questionnaire_names():
#     """
#     Add questionnaire_name column to questionnaire_fields table.
#     Allows organizations to create multiple distinct questionnaires.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         # Add questionnaire_name column
#         cur.execute("""
#             ALTER TABLE questionnaire_fields
#                 ADD COLUMN IF NOT EXISTS questionnaire_name VARCHAR(255);
#         """)

#         # Set default name for existing fields (per client)
#         # Group existing fields under "Main Questionnaire" for each client
#         cur.execute("""
#             UPDATE questionnaire_fields
#             SET questionnaire_name = 'Main Questionnaire'
#             WHERE questionnaire_name IS NULL;
#         """)

#         # Now make it NOT NULL with default
#         cur.execute("""
#             ALTER TABLE questionnaire_fields
#                 ALTER COLUMN questionnaire_name SET NOT NULL,
#                 ALTER COLUMN questionnaire_name SET DEFAULT 'Main Questionnaire';
#         """)

#         # Add composite index for efficient queries by client_id + questionnaire_name
#         cur.execute("""
#             CREATE INDEX IF NOT EXISTS idx_questionnaire_fields_client_qname
#                 ON questionnaire_fields(client_id, questionnaire_name);
#         """)

#         # Add unique constraint to prevent duplicate field labels within same questionnaire
#         # Format: client_id + questionnaire_name + field_label must be unique
#         cur.execute("""
#             CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_field_per_questionnaire
#                 ON questionnaire_fields(client_id, questionnaire_name, field_label);
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Questionnaire names migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in questionnaire names migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_2fa_and_email():
#     """
#     Add email storage to users table and create OTP/password-reset token tables.
#     Supports email-based 2FA and password reset via AWS SES.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         # Add encrypted email column to users table
#         cur.execute("""
#             ALTER TABLE users
#                 ADD COLUMN IF NOT EXISTS email_enc BYTEA;
#         """)

#         # OTP tokens for 2FA - one active token per user at a time
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS otp_tokens (
#                 id           SERIAL PRIMARY KEY,
#                 user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
#                 token_hash   VARCHAR(64) NOT NULL,
#                 expires_at   TIMESTAMPTZ NOT NULL,
#                 used         BOOLEAN NOT NULL DEFAULT FALSE,
#                 attempts     INTEGER NOT NULL DEFAULT 0,
#                 created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
#             );
#         """)

#         # Password reset tokens - one active token per user at a time
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS password_reset_tokens (
#                 id           SERIAL PRIMARY KEY,
#                 user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
#                 token_hash   VARCHAR(64) NOT NULL,
#                 expires_at   TIMESTAMPTZ NOT NULL,
#                 used         BOOLEAN NOT NULL DEFAULT FALSE,
#                 created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
#             );
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("2FA and email migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in 2FA/email migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_questionnaire_tracking_to_submissions():
#     """
#     Add questionnaire_name to submissions table to track which specific
#     questionnaire the submission is for.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         # Add questionnaire_name column to submissions
#         cur.execute("""
#             ALTER TABLE submissions
#                 ADD COLUMN IF NOT EXISTS questionnaire_name VARCHAR(255);
#         """)

#         # Set default for existing submissions
#         cur.execute("""
#             UPDATE submissions
#             SET questionnaire_name = 'Main Questionnaire'
#             WHERE questionnaire_name IS NULL AND client_id IS NOT NULL;
#         """)

#         # Add index for efficient queries
#         cur.execute("""
#             CREATE INDEX IF NOT EXISTS idx_submissions_client_qname
#                 ON submissions(client_id, questionnaire_name);
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Submissions questionnaire tracking migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in submissions questionnaire tracking migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_audit_client_id():
#     """
#     Add client_id column to audit_logs for per-client filtering.
#     Each client should only see audit logs related to their own data.
#     Backfills existing rows where the client can be determined.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         # Add client_id column (nullable - some logs are not client-specific)
#         cur.execute("""
#             ALTER TABLE audit_logs
#                 ADD COLUMN IF NOT EXISTS client_id INT;
#         """)

#         # Add index for fast filtering by client
#         cur.execute("""
#             CREATE INDEX IF NOT EXISTS idx_audit_client_id
#                 ON audit_logs(client_id);
#         """)

#         # Backfill: where actor is a client, set client_id = actor_id
#         cur.execute("""
#             UPDATE audit_logs
#             SET client_id = actor_id
#             WHERE actor_type = 'client' AND client_id IS NULL AND actor_id IS NOT NULL;
#         """)

#         # Backfill: where details JSONB contains client_id
#         cur.execute("""
#             UPDATE audit_logs
#             SET client_id = (details->>'client_id')::INT
#             WHERE client_id IS NULL
#               AND details->>'client_id' IS NOT NULL;
#         """)

#         # Backfill: where target_table is 'submissions' and target_id links to a submission
#         cur.execute("""
#             UPDATE audit_logs al
#             SET client_id = s.client_id
#             FROM submissions s
#             WHERE al.target_table = 'submissions'
#               AND al.target_id = s.submission_id
#               AND al.client_id IS NULL
#               AND s.client_id IS NOT NULL;
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Audit client_id migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in audit client_id migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_auditors_table():
#     """
#     Create auditors table for external auditor access to the full audit trail.
#     Auditors see all logs unfiltered, unlike clients who only see their own.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS auditors (
#                 auditor_id SERIAL PRIMARY KEY,
#                 username VARCHAR(100) UNIQUE NOT NULL,
#                 password_hash VARCHAR(255) NOT NULL,
#                 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
#             );
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Auditors table migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in auditors table migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_last_login_column():
#     """
#     Add last_login column to users table for data retention tracking.
#     GDPR Article 5(1)(e) - Storage Limitation: data should not be kept
#     longer than necessary. This column tracks when users last logged in
#     so inactive accounts can be identified for cleanup.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         cur.execute("""
#             ALTER TABLE users
#                 ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;
#         """)

#         # Backfill existing users with current timestamp
#         cur.execute("""
#             UPDATE users SET last_login = NOW() WHERE last_login IS NULL;
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Last login column migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in last login migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_data_breaches_table():
#     """
#     Create data_breaches table for GDPR Article 33-34 breach notification.
#     Tracks data breaches, their severity, status, and the 72-hour
#     reporting deadline to the supervisory authority.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS data_breaches (
#                 breach_id SERIAL PRIMARY KEY,
#                 title VARCHAR(255) NOT NULL,
#                 description TEXT,
#                 severity VARCHAR(20) NOT NULL DEFAULT 'medium',
#                 discovered_at TIMESTAMPTZ DEFAULT NOW(),
#                 reported_at TIMESTAMPTZ,
#                 resolved_at TIMESTAMPTZ,
#                 affected_users_count INT DEFAULT 0,
#                 data_types_affected TEXT,
#                 remedial_actions TEXT,
#                 reported_by INT,
#                 status VARCHAR(20) DEFAULT 'open',
#                 created_at TIMESTAMPTZ DEFAULT NOW()
#             );
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Data breaches table migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in data breaches table migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_dsr_table():
#     """
#     Create data_subject_requests table for GDPR Articles 12-23.
#     Tracks formal data subject requests with 30-day response deadlines.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS data_subject_requests (
#                 dsr_id          SERIAL PRIMARY KEY,
#                 user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
#                 username        VARCHAR(100),
#                 request_type    VARCHAR(30) NOT NULL,
#                 status          VARCHAR(20) NOT NULL DEFAULT 'pending',
#                 created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
#                 completed_at    TIMESTAMPTZ,
#                 deadline        TIMESTAMPTZ NOT NULL,
#                 notes           TEXT,
#                 source          VARCHAR(20) DEFAULT 'web'
#             );
#         """)

#         cur.execute("""
#             CREATE INDEX IF NOT EXISTS idx_dsr_user_id ON data_subject_requests(user_id);
#         """)

#         cur.execute("""
#             CREATE INDEX IF NOT EXISTS idx_dsr_status ON data_subject_requests(status);
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("DSR table migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in DSR table migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def add_breach_notifications_table():
#     """
#     Create breach_notifications table for GDPR Article 34.
#     Tracks email notifications sent to users about data breaches.
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS breach_notifications (
#                 notification_id   SERIAL PRIMARY KEY,
#                 breach_id         INTEGER NOT NULL REFERENCES data_breaches(breach_id),
#                 user_id           INTEGER REFERENCES users(id) ON DELETE SET NULL,
#                 email_address     VARCHAR(255) NOT NULL,
#                 sent_at           TIMESTAMPTZ,
#                 status            VARCHAR(20) NOT NULL DEFAULT 'pending',
#                 error_message     TEXT,
#                 created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
#             );
#         """)

#         cur.execute("""
#             CREATE INDEX IF NOT EXISTS idx_breach_notif_breach
#                 ON breach_notifications(breach_id);
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Breach notifications table migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in breach notifications table migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False


# def remove_redundant_tables_and_columns():
#     """
#     Remove the medical_data table (unused, medical fields are stored
#     encrypted in the answers table based on field category).
#     Remove the consent column from submissions (always TRUE on insert,
#     consent_withdrawn is what the system actually checks).
#     """
#     conn = get_db_connection()
#     if conn is None:
#         return False

#     try:
#         cur = conn.cursor()

#         # Drop medical_data table, not used anywhere in the codebase.
#         # Medical fields are handled via the answers table with
#         # pgp_sym_encrypt when category = 'Medical'.
#         cur.execute("""
#             DROP TABLE IF EXISTS medical_data CASCADE;
#         """)

#         # Remove redundant consent column from submissions.
#         # This column is always set to TRUE on insert (consent is required
#         # to submit). The consent_withdrawn column is what the system
#         # actually reads to determine current consent status.
#         cur.execute("""
#             ALTER TABLE submissions
#                 DROP COLUMN IF EXISTS consent;
#         """)

#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info("Redundant table/column cleanup migration completed")
#         return True
#     except Exception as e:
#         logger.error("Error in cleanup migration: %s", e)
#         conn.rollback()
#         conn.close()
#         return False
