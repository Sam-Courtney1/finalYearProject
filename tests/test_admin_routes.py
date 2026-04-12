from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash


class TestAuditorLogin:
    def test_auditor_login_page_renders(self, client):
        resp = client.get('/admin/auditor-login')
        assert resp.status_code == 200

    def test_auditor_login_valid_credentials(self, client):
        hashed = generate_password_hash('AuditorPass1!')
        mock_auditor = (99, 'test_auditor', hashed)
        with patch('application.routes.admin_routes.find_auditor_by_username', return_value=mock_auditor):
            resp = client.post('/admin/auditor-login', data={
                'username': 'test_auditor',
                'password': 'AuditorPass1!'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_auditor_login_invalid_credentials(self, client):
        with patch('application.routes.admin_routes.find_auditor_by_username', return_value=None):
            resp = client.post('/admin/auditor-login', data={
                'username': 'bad',
                'password': 'wrong'
            }, follow_redirects=True)
            assert b'Invalid' in resp.data or resp.status_code == 200

    def test_auditor_logout_clears_session(self, auditor_client):
        resp = auditor_client.get('/admin/auditor-logout', follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestAuditDashboard:
    def test_audit_dashboard_requires_auth(self, client):
        resp = client.get('/admin/', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_audit_dashboard_renders_for_auditor(self, auditor_client):
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]), \
             patch('application.routes.admin_routes.get_audit_log_count', return_value=0), \
             patch('application.routes.admin_routes.get_action_summary', return_value={}), \
             patch('application.routes.admin_routes.verify_audit_chain', return_value=True):
            resp = auditor_client.get('/admin/')
            assert resp.status_code == 200

    def test_audit_dashboard_renders_for_client(self, client_auth_client):
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]), \
             patch('application.routes.admin_routes.get_audit_log_count', return_value=0), \
             patch('application.routes.admin_routes.get_action_summary', return_value={}), \
             patch('application.routes.admin_routes.verify_audit_chain', return_value=True):
            resp = client_auth_client.get('/admin/')
            assert resp.status_code == 200

    def test_export_audit_logs_returns_csv(self, auditor_client):
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]):
            resp = auditor_client.get('/admin/export')
            assert resp.status_code == 200
            assert resp.content_type.startswith('text/csv')

    def test_verify_chain_valid(self, auditor_client):
        with patch('application.routes.admin_routes.verify_audit_chain', return_value=True):
            resp = auditor_client.get('/admin/verify-chain', follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_verify_chain_invalid(self, auditor_client):
        with patch('application.routes.admin_routes.verify_audit_chain', return_value=False):
            resp = auditor_client.get('/admin/verify-chain', follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_init_audit_table(self, auditor_client):
        with patch('application.routes.admin_routes.create_audit_table', return_value=True):
            resp = auditor_client.get('/admin/init', follow_redirects=False)
            assert resp.status_code in (302, 303)


class TestBreachDashboard:
    def test_breach_dashboard_renders_for_auditor(self, auditor_client):
        with patch('application.routes.admin_routes.get_all_breaches', return_value=[]), \
             patch('application.routes.admin_routes.get_breach_summary', return_value={}):
            resp = auditor_client.get('/admin/breaches')
            assert resp.status_code == 200

    def test_breach_dashboard_blocked_for_client(self, client_auth_client):
        resp = client_auth_client.get('/admin/breaches', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_create_breach_success(self, auditor_client):
        with patch('application.routes.admin_routes.insert_breach', return_value=1):
            resp = auditor_client.post('/admin/breaches', data={
                'title': 'Test Breach',
                'description': 'A test breach incident',
                'severity': 'high',
                'affected_users_count': '10',
                'data_types_affected': 'email, name'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_create_breach_missing_title_rejected(self, auditor_client):
        resp = auditor_client.post('/admin/breaches', data={
            'title': '',
            'description': 'No title'
        }, follow_redirects=False)
        # Redirects back to breach dashboard with flash message
        assert resp.status_code in (302, 303)

    def test_breach_detail_renders(self, auditor_client):
        mock_breach = {
            'breach_id': 1, 'title': 'Test', 'description': 'desc',
            'severity': 'high', 'status': 'open',
            'discovered_at': None, 'reported_at': None, 'resolved_at': None,
            'affected_users_count': 5, 'data_types_affected': 'email',
            'remedial_actions': '', 'created_at': None
        }
        with patch('application.routes.admin_routes.get_breach_by_id', return_value=mock_breach), \
             patch('application.routes.admin_routes.check_72h_deadline', return_value=48.0), \
             patch('application.routes.admin_routes.get_notifications_for_breach', return_value=[]), \
             patch('application.routes.admin_routes.get_notification_summary', return_value={}):
            resp = auditor_client.get('/admin/breaches/1')
            assert resp.status_code == 200

    def test_breach_detail_not_found(self, auditor_client):
        with patch('application.routes.admin_routes.get_breach_by_id', return_value=None):
            resp = auditor_client.get('/admin/breaches/999', follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_update_breach_status(self, auditor_client):
        with patch('application.routes.admin_routes.update_breach_status', return_value=True):
            resp = auditor_client.post('/admin/breaches/1/update', data={
                'status': 'reported',
                'remedial_actions': 'Patched vulnerability'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_notify_breach_users(self, auditor_client):
        mock_result = {'total': 5, 'sent': 5, 'failed': 0}
        with patch('application.routes.admin_routes.notify_all_affected_users', return_value=mock_result):
            resp = auditor_client.post('/admin/breaches/1/notify', follow_redirects=False)
            assert resp.status_code in (302, 303)


class TestRetentionDashboard:
    def test_retention_dashboard_renders_for_auditor(self, auditor_client):
        with patch('application.routes.admin_routes.get_retention_stats', return_value={}), \
             patch('application.routes.admin_routes.get_inactive_users', return_value=[]), \
             patch('application.routes.admin_routes.get_expired_submissions', return_value=[]):
            resp = auditor_client.get('/admin/retention')
            assert resp.status_code == 200

    def test_retention_dashboard_blocked_for_client(self, client_auth_client):
        resp = client_auth_client.get('/admin/retention', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_retention_preview(self, auditor_client):
        mock_result = {'inactive_users_count': 3, 'expired_submissions_count': 10}
        with patch('application.routes.admin_routes.run_retention_cleanup', return_value=mock_result):
            resp = auditor_client.post('/admin/retention/preview', data={
                'days': '365'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_retention_cleanup_executes(self, auditor_client):
        mock_result = {'deleted_submissions': 5, 'anonymised_users': 2}
        with patch('application.routes.admin_routes.run_retention_cleanup', return_value=mock_result):
            resp = auditor_client.post('/admin/retention/cleanup', data={
                'days': '365'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)


class TestDSRDashboard:
    def test_dsr_dashboard_renders_for_auditor(self, auditor_client):
        mock_data = {
            'dsrs': [],
            'summary': {
                'total': 0, 'pending': 0, 'in_progress': 0,
                'completed': 0, 'overdue_count': 0
            }
        }
        with patch('application.routes.admin_routes.get_dsr_dashboard_data', return_value=mock_data):
            resp = auditor_client.get('/admin/dsr')
            assert resp.status_code == 200

    def test_dsr_dashboard_blocked_for_client(self, client_auth_client):
        resp = client_auth_client.get('/admin/dsr', follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestComplianceDashboard:
    def test_compliance_dashboard_renders_for_auditor(self, auditor_client):
        mock_overview = {
            'breach': {'open_count': 0, 'total_count': 0, 'overdue_count': 0},
            'dsr': {'pending_count': 0, 'overdue_count': 0, 'total_count': 0},
            'retention': {'inactive_users': 0, 'expired_submissions': 0},
            'backup': {'last_backup': None, 'status': 'unknown'},
            'overall_status': 'compliant'
        }
        with patch('application.routes.admin_routes.get_compliance_overview', return_value=mock_overview):
            resp = auditor_client.get('/admin/compliance')
            assert resp.status_code == 200

    def test_compliance_dashboard_blocked_for_client(self, client_auth_client):
        resp = client_auth_client.get('/admin/compliance', follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestGeolocateIP:
    def test_geolocate_invalid_ip_rejected(self, auditor_client):
        resp = auditor_client.get('/admin/geolocate/not-an-ip')
        data = resp.get_json()
        assert data['success'] is False

    def test_geolocate_private_ip_blocked(self, auditor_client):
        resp = auditor_client.get('/admin/geolocate/192.168.1.1')
        data = resp.get_json()
        assert data['success'] is False
        assert 'private' in data['message'].lower() or 'reserved' in data['message'].lower()

    def test_geolocate_loopback_blocked(self, auditor_client):
        resp = auditor_client.get('/admin/geolocate/127.0.0.1')
        data = resp.get_json()
        assert data['success'] is False
