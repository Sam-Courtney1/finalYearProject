import hashlib
import json
import logging
from datetime import datetime
from data.db_connection import get_db_connection, get_db

logger = logging.getLogger(__name__)

"""
Audit Logging Database Operations
GDPR Article 32 - Security of Processing

This module handles all database operations for the audit logging system.
It provides tamper evident logging through hash chaining, where each log
entry contains a hash of the previous entry, making it detectable if
logs are modified or deleted.
"""

def create_audit_table():
    """
    Creates the audit_logs table if it doesn't exist.
    Call this during application startup.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
                hash_timestamp TEXT,
                actor_id INT,
                actor_type VARCHAR(20),
                action VARCHAR(50) NOT NULL,
                target_table VARCHAR(50),
                target_id INT,
                ip_address INET,
                user_agent TEXT,
                details JSONB,
                previous_hash VARCHAR(64),
                current_hash VARCHAR(64)
            );

            CREATE INDEX IF NOT EXISTS idx_audit_actor
                ON audit_logs(actor_id, actor_type);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_target
                ON audit_logs(target_table, target_id);
            CREATE INDEX IF NOT EXISTS idx_audit_action
                ON audit_logs(action);
        """)

        """
        Create indexs above to allow for much faster searching
        For example when executing select * from audit_logs where action = 'delete';
        Rather then going though all rows, an index is kept to store what rows are delete's
        This means that not every row is needed to be searched
        """

        conn.commit()
        cur.close()
        conn.close()
        logger.info("Audit table created/verified successfully")
        return True
    except Exception as e:
        logger.error("Error creating audit table: %s", e)
        conn.close()
        return False


def get_last_hash():
    """
    Retrieves the hash of the most recent audit log entry.
    Used for tamper evident chain linking.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT current_hash FROM audit_logs
                ORDER BY log_id DESC LIMIT 1
            """)
            result = cur.fetchone()
            # Return the latest hash or if there is none
            # return GENESIS to start the chain
            return result[0] if result else "GENESIS"
    except Exception as e:
        logger.error("Error getting last hash: %s", e)
        return "GENESIS"


def compute_hash(timestamp, actor_id, actor_type, action, target_table,
                 target_id, ip_address, details, previous_hash):
    """
    Computes SHA-256 hash of log entry data for tamper evidence.
    Uses sort_keys=True for consistent JSON ordering.
    """
    # Normalize ip_address to string for consistent hashing as postgres can store as INET data type
    ip_str = str(ip_address) if ip_address else None
    # Use sort_keys to ensure consistent ordering regardless of dict key order
    # Sorts alphabetically as there is no guarenteed order
    # This is important as the output for the same data is now forced to be identical
    # IE {"b":2, "a":1}, {"a":1, "b":2}. With sort_keys=True A will always be first
    details_str = json.dumps(details, sort_keys=True) if details else 'null'
    # Join all data together to build a string
    data = f"{timestamp}|{actor_id}|{actor_type}|{action}|{target_table}|{target_id}|{ip_str}|{details_str}|{previous_hash}"
    # The data is then converted into bytes and sha256 runs on those bytes
    # .hexdigest() returns the result as a 64 character hex string
    return hashlib.sha256(data.encode()).hexdigest()


def insert_audit_log(actor_id, actor_type, action, target_table=None,
                     target_id=None, ip_address=None, user_agent=None,
                     details=None, client_id=None):
    """
    Inserts a new audit log entry with hash chain linking.
    client_id tags which client this log relates to (for per-client filtering).
    It is NOT included in the hash computation - it is metadata only.
    """
    try:
        # Get previous hash for chain linking
        previous_hash = get_last_hash()
        timestamp = datetime.utcnow().isoformat()

        # Compute hash for this entry (client_id excluded from hash)
        current_hash = compute_hash(
            timestamp, actor_id, actor_type, action, target_table,
            target_id, ip_address, details, previous_hash
        )

        with get_db() as (conn, cur):
            cur.execute("""
                INSERT INTO audit_logs
                (timestamp, hash_timestamp, actor_id, actor_type, action, target_table, target_id,
                 ip_address, user_agent, details, previous_hash, current_hash, client_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING log_id
            """, (
                timestamp, timestamp, actor_id, actor_type, action, target_table, target_id,
                ip_address, user_agent, json.dumps(details) if details else None,
                previous_hash, current_hash, client_id
            ))

            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Error inserting audit log: %s", e)
        return None

# Use the value's the user has passed or set to NONE
def get_audit_logs(limit=100, offset=0, actor_id=None, actor_type=None,
                   action=None, start_date=None, end_date=None, client_id=None):
    """
    Retrieves audit logs with optional filtering.
    Limit param above is overriden in admin_routes.py
    In the audit_dashboard function in per page variable.
    When client_id is provided, only logs belonging to that client are returned.
    """
    try:
        with get_db() as (conn, cur):
            # Build query with filters, built with 1=1 so that futher filter can be applied
            # By just appending them to the query
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []

            if client_id is not None:
                query += " AND client_id = %s"
                params.append(client_id)

            if actor_id is not None:
                query += " AND actor_id = %s"
                params.append(actor_id)

            if actor_type is not None:
                query += " AND actor_type = %s"
                params.append(actor_type)

            if action is not None:
                query += " AND action = %s"
                params.append(action)

            if start_date is not None:
                query += " AND timestamp >= %s"
                params.append(start_date)

            if end_date is not None:
                query += " AND timestamp <= %s"
                params.append(end_date)

            query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"

            # Add both limit and offset to params
            params.extend([limit, offset])

            # Execute the sql
            cur.execute(query, params)
            logs = cur.fetchall()

            # Get column names for dict conversion
            columns = [desc[0] for desc in cur.description]

            # Convert to list of dicts
            return [dict(zip(columns, log)) for log in logs]
    except Exception as e:
        logger.error("Error retrieving audit logs: %s", e)
        return []


def get_audit_log_count(actor_id=None, actor_type=None, action=None,
                        start_date=None, end_date=None, client_id=None):
    """
    Gets total count of audit logs matching filters for pagination.
    When client_id is provided, only counts logs belonging to that client.
    """
    try:
        with get_db() as (conn, cur):
            query = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
            params = []

            if client_id is not None:
                query += " AND client_id = %s"
                params.append(client_id)

            if actor_id is not None:
                query += " AND actor_id = %s"
                params.append(actor_id)

            if actor_type is not None:
                query += " AND actor_type = %s"
                params.append(actor_type)

            if action is not None:
                query += " AND action = %s"
                params.append(action)

            if start_date is not None:
                query += " AND timestamp >= %s"
                params.append(start_date)

            if end_date is not None:
                query += " AND timestamp <= %s"
                params.append(end_date)

            cur.execute(query, params)
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Error counting audit logs: %s", e)
        return 0


def verify_audit_chain():
    """
    Verifies the integrity of the audit log hash chain.
    Returns True if chain is intact, False if tampering detected.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT log_id, hash_timestamp, actor_id, actor_type, action,
                       target_table, target_id, ip_address, details,
                       previous_hash, current_hash
                FROM audit_logs ORDER BY log_id ASC
            """)
            logs = cur.fetchall()

        if not logs:
            return True  # Empty log is valid

        expected_prev_hash = "GENESIS"

        for log in logs:
            (log_id, hash_timestamp, actor_id, actor_type, action,
             target_table, target_id, ip_address, details,
             previous_hash, current_hash) = log

            # Check previous hash matches (chain linking)
            if previous_hash != expected_prev_hash:
                logger.warning("Chain broken at log_id %s: expected prev_hash %s, got %s",
                             log_id, expected_prev_hash, previous_hash)
                return False

            # Verify current hash matches the data (tamper detection)
            # Use the exact timestamp string that was stored during insertion
            computed_hash = compute_hash(
                hash_timestamp,
                actor_id, actor_type, action, target_table,
                target_id, ip_address,
                details, previous_hash
            )

            if computed_hash != current_hash:
                logger.warning("Tamper detected at log_id %s: stored hash doesn't match computed hash", log_id)
                return False

            expected_prev_hash = current_hash

        return True
    except Exception as e:
        logger.error("Error verifying audit chain: %s", e)
        return None


def get_user_audit_logs(user_id, limit=50):
    """
    Gets audit logs for a specific user (for privacy dashboard).
    """
    return get_audit_logs(limit=limit, actor_id=user_id, actor_type='user')


def get_logs_for_record(target_table, target_id):
    """
    Gets all audit logs related to a specific database record.
    Useful for tracking history of a particular user's data.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute("""
                SELECT * FROM audit_logs
                WHERE target_table = %s AND target_id = %s
                ORDER BY timestamp DESC
            """, (target_table, target_id))

            logs = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

            return [dict(zip(columns, log)) for log in logs]
    except Exception as e:
        logger.error("Error retrieving record logs: %s", e)
        return []


def find_auditor_by_username(username):
    """
    Finds an auditor by username. Returns (auditor_id, username, password_hash) or None.
    """
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT auditor_id, username, password_hash FROM auditors WHERE username = %s",
                (username,)
            )
            return cur.fetchone()
    except Exception as e:
        logger.error("Error finding auditor: %s", e)
        return None


def get_action_summary(start_date=None, end_date=None, client_id=None):
    """
    Gets summary statistics of actions for dashboard.
    When client_id is provided, only counts actions for that client.
    """
    try:
        with get_db() as (conn, cur):
            query = """
                SELECT action, COUNT(*) as count
                FROM audit_logs
                WHERE 1=1
            """
            params = []

            if client_id is not None:
                query += " AND client_id = %s"
                params.append(client_id)

            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)

            query += " GROUP BY action ORDER BY count DESC"

            cur.execute(query, params)
            results = cur.fetchall()

            return {action: count for action, count in results}
    except Exception as e:
        logger.error("Error getting action summary: %s", e)
        return {}
