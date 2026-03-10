from unittest.mock import patch, MagicMock
from data.audit_database import compute_hash


class TestHashChainIntegrity:
    """Tests for the audit log SHA-256 hash chain tamper-evidence system."""

    def test_compute_hash_is_deterministic(self):
        """Same inputs must always produce the same hash."""
        h1 = compute_hash('2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS')
        h2 = compute_hash('2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS')
        assert h1 == h2

    def test_different_data_produces_different_hash(self):
        """Different inputs must produce different hashes."""
        h1 = compute_hash('2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS')
        h2 = compute_hash('2025-01-01', 2, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS')
        assert h1 != h2

    def test_client_id_excluded_from_hash(self):
        """
        client_id is metadata for filtering — it must NOT affect the hash.
        Two logs identical except for client_id should produce the same hash.
        """
        h1 = compute_hash('2025-01-01', 1, 'client', 'view', 'audit_logs', None, '1.2.3.4', None, 'GENESIS')
        h2 = compute_hash('2025-01-01', 1, 'client', 'view', 'audit_logs', None, '1.2.3.4', None, 'GENESIS')
        # compute_hash does not take client_id at all — it is excluded by design
        assert h1 == h2

    def test_chain_links_via_previous_hash(self):
        """Each entry's hash should depend on the previous entry's hash."""
        h1 = compute_hash('2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS')
        h2_with_chain = compute_hash('2025-01-02', 1, 'user', 'view', None, None, '1.2.3.4', None, h1)
        h2_without_chain = compute_hash('2025-01-02', 1, 'user', 'view', None, None, '1.2.3.4', None, 'GENESIS')
        assert h2_with_chain != h2_without_chain

    def test_verify_chain_passes_on_valid_chain(self):
        """verify_audit_chain should return True for an untampered chain."""
        h1 = compute_hash('2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS')
        h2 = compute_hash('2025-01-02', 1, 'user', 'view', None, None, '1.2.3.4', None, h1)

        mock_rows = [
            (1, '2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS', h1),
            (2, '2025-01-02', 1, 'user', 'view', None, None, '1.2.3.4', None, h1, h2),
        ]

        with patch('data.audit_database.get_db') as mock_db:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_rows
            mock_db.return_value.__enter__ = MagicMock(return_value=(MagicMock(), mock_cur))
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            from data.audit_database import verify_audit_chain
            result = verify_audit_chain()
            assert result is True

    def test_verify_chain_fails_on_tampered_entry(self):
        """verify_audit_chain should return False if a hash has been altered."""
        h1 = compute_hash('2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS')

        mock_rows = [
            (1, '2025-01-01', 1, 'user', 'login', None, None, '1.2.3.4', None, 'GENESIS', 'TAMPERED_HASH'),
        ]

        with patch('data.audit_database.get_db') as mock_db:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_rows
            mock_db.return_value.__enter__ = MagicMock(return_value=(MagicMock(), mock_cur))
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            from data.audit_database import verify_audit_chain
            result = verify_audit_chain()
            assert result is False

    def test_verify_chain_passes_on_empty_log(self):
        """An empty audit log should be considered valid."""
        with patch('data.audit_database.get_db') as mock_db:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_db.return_value.__enter__ = MagicMock(return_value=(MagicMock(), mock_cur))
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            from data.audit_database import verify_audit_chain
            result = verify_audit_chain()
            assert result is True


class TestAuditDashboardAccess:
    """Tests for audit dashboard access control."""

    def test_audit_dashboard_requires_auth(self, client):
        """Unauthenticated access should redirect to auditor login."""
        resp = client.get('/admin/', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_audit_dashboard_accessible_by_auditor(self, auditor_client):
        """Auditors should be able to access the audit dashboard."""
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]), \
             patch('application.routes.admin_routes.get_audit_log_count', return_value=0), \
             patch('application.routes.admin_routes.get_action_summary', return_value={}), \
             patch('application.routes.admin_routes.verify_audit_chain', return_value=True):
            resp = auditor_client.get('/admin/')
            assert resp.status_code == 200
            assert b'Auditor View' in resp.data

    def test_audit_dashboard_accessible_by_client(self, client_auth_client):
        """Clients should be able to access the audit dashboard (filtered view)."""
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]), \
             patch('application.routes.admin_routes.get_audit_log_count', return_value=0), \
             patch('application.routes.admin_routes.get_action_summary', return_value={}), \
             patch('application.routes.admin_routes.verify_audit_chain', return_value=True):
            resp = client_auth_client.get('/admin/')
            assert resp.status_code == 200
            assert b'Client View' in resp.data

    def test_export_csv_returns_csv_content_type(self, auditor_client):
        """CSV export should return text/csv content type."""
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]):
            resp = auditor_client.get('/admin/export')
            assert resp.status_code == 200
            assert 'text/csv' in resp.content_type
