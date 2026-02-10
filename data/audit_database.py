import hashlib
import json
from datetime import datetime
from data.db_connection import get_db_connection

"""
Audit Logging Database Operations
GDPR Article 32 - Security of Processing

This module handles all database operations for the audit logging system.
It provides tamper-evident logging through hash chaining, where each log
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
        conn.commit()
        cur.close()
        conn.close()
        print("Audit table created/verified successfully")
        return True
    except Exception as e:
        print(f"Error creating audit table: {e}")
        conn.close()
        return False


def get_last_hash():
    """
    Retrieves the hash of the most recent audit log entry.
    Used for tamper-evident chain linking.
    """
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT current_hash FROM audit_logs
            ORDER BY log_id DESC LIMIT 1
        """)
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else "GENESIS"
    except Exception as e:
        print(f"Error getting last hash: {e}")
        conn.close()
        return "GENESIS"


def compute_hash(timestamp, actor_id, actor_type, action, target_table,
                 target_id, ip_address, details, previous_hash):
    """
    Computes SHA-256 hash of log entry data for tamper evidence.
    Uses sort_keys=True for consistent JSON ordering across insert/verify.
    """
    # Normalize ip_address to string for consistent hashing
    ip_str = str(ip_address) if ip_address else None
    # Use sort_keys to ensure consistent ordering regardless of dict key order
    details_str = json.dumps(details, sort_keys=True) if details else 'null'
    data = f"{timestamp}|{actor_id}|{actor_type}|{action}|{target_table}|{target_id}|{ip_str}|{details_str}|{previous_hash}"
    return hashlib.sha256(data.encode()).hexdigest()


def insert_audit_log(actor_id, actor_type, action, target_table=None,
                     target_id=None, ip_address=None, user_agent=None,
                     details=None):
    """
    Inserts a new audit log entry with hash chain linking.

    Parameters:
    - actor_id: ID of user or client performing action
    - actor_type: 'user', 'client', or 'system'
    - action: 'login', 'logout', 'view', 'create', 'update', 'delete', 'export', 'login_failed'
    - target_table: Table being accessed (optional)
    - target_id: ID of record being accessed (optional)
    - ip_address: Client IP address (optional)
    - user_agent: Client browser/user agent (optional)
    - details: Additional context as dict (optional)
    """
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        # Get previous hash for chain linking
        previous_hash = get_last_hash()
        timestamp = datetime.utcnow().isoformat()

        # Compute hash for this entry
        current_hash = compute_hash(
            timestamp, actor_id, actor_type, action, target_table,
            target_id, ip_address, details, previous_hash
        )

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_logs
            (timestamp, hash_timestamp, actor_id, actor_type, action, target_table, target_id,
             ip_address, user_agent, details, previous_hash, current_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING log_id
        """, (
            timestamp, timestamp, actor_id, actor_type, action, target_table, target_id,
            ip_address, user_agent, json.dumps(details) if details else None,
            previous_hash, current_hash
        ))

        log_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return log_id
    except Exception as e:
        print(f"Error inserting audit log: {e}")
        conn.close()
        return None


def get_audit_logs(limit=100, offset=0, actor_id=None, actor_type=None,
                   action=None, start_date=None, end_date=None):
    """
    Retrieves audit logs with optional filtering.

    Parameters:
    - limit: Maximum number of logs to return
    - offset: Number of logs to skip (for pagination)
    - actor_id: Filter by specific actor
    - actor_type: Filter by 'user' or 'client'
    - action: Filter by action type
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date
    """
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cur = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

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
        params.extend([limit, offset])

        cur.execute(query, params)
        logs = cur.fetchall()

        # Get column names for dict conversion
        columns = [desc[0] for desc in cur.description]

        cur.close()
        conn.close()

        # Convert to list of dicts
        return [dict(zip(columns, log)) for log in logs]
    except Exception as e:
        print(f"Error retrieving audit logs: {e}")
        conn.close()
        return []


def get_audit_log_count(actor_id=None, actor_type=None, action=None,
                        start_date=None, end_date=None):
    """
    Gets total count of audit logs matching filters (for pagination).
    """
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cur = conn.cursor()

        query = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
        params = []

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
        count = cur.fetchone()[0]

        cur.close()
        conn.close()
        return count
    except Exception as e:
        print(f"Error counting audit logs: {e}")
        conn.close()
        return 0


def verify_audit_chain():
    """
    Verifies the integrity of the audit log hash chain.
    Returns True if chain is intact, False if tampering detected.
    """
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT log_id, hash_timestamp, actor_id, actor_type, action,
                   target_table, target_id, ip_address, details,
                   previous_hash, current_hash
            FROM audit_logs ORDER BY log_id ASC
        """)
        logs = cur.fetchall()
        cur.close()
        conn.close()

        if not logs:
            return True  # Empty log is valid

        expected_prev_hash = "GENESIS"

        for log in logs:
            (log_id, hash_timestamp, actor_id, actor_type, action,
             target_table, target_id, ip_address, details,
             previous_hash, current_hash) = log

            # Check previous hash matches (chain linking)
            if previous_hash != expected_prev_hash:
                print(f"Chain broken at log_id {log_id}: expected prev_hash {expected_prev_hash}, got {previous_hash}")
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
                print(f"Tamper detected at log_id {log_id}: stored hash doesn't match computed hash")
                print(f"  Action: {action}, Actor: {actor_type}:{actor_id}")
                return False

            expected_prev_hash = current_hash

        return True
    except Exception as e:
        print(f"Error verifying audit chain: {e}")
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
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM audit_logs
            WHERE target_table = %s AND target_id = %s
            ORDER BY timestamp DESC
        """, (target_table, target_id))

        logs = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        cur.close()
        conn.close()

        return [dict(zip(columns, log)) for log in logs]
    except Exception as e:
        print(f"Error retrieving record logs: {e}")
        conn.close()
        return []


def get_action_summary(start_date=None, end_date=None):
    """
    Gets summary statistics of actions for dashboard.
    """
    conn = get_db_connection()
    if conn is None:
        return {}

    try:
        cur = conn.cursor()

        query = """
            SELECT action, COUNT(*) as count
            FROM audit_logs
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        query += " GROUP BY action ORDER BY count DESC"

        cur.execute(query, params)
        results = cur.fetchall()

        cur.close()
        conn.close()

        return {action: count for action, count in results}
    except Exception as e:
        print(f"Error getting action summary: {e}")
        conn.close()
        return {}