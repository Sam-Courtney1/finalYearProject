"""
Tests for security hardening fixes:
- CSV formula injection sanitizer
- JWT token edge cases
- API age validation
- Audit dashboard date_range bad input
- Audit hash chain integrity
"""
import json
from unittest.mock import patch, MagicMock
from application.routes.admin_routes import _sanitize_csv_value
from application.services.jwt_utils import create_token, decode_token
from data.audit_database import compute_hash


def auth_header(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


# ── CSV Formula Injection Sanitizer ──────────────────────────────

class TestCSVSanitizer:
    def test_none_returns_empty_string(self):
        assert _sanitize_csv_value(None) == ''

    def test_normal_string_unchanged(self):
        assert _sanitize_csv_value('hello') == 'hello'

    def test_number_unchanged(self):
        assert _sanitize_csv_value(42) == '42'

    def test_equals_sign_prefixed(self):
        assert _sanitize_csv_value('=CMD("calc")') == "'" + '=CMD("calc")'

    def test_plus_sign_prefixed(self):
        assert _sanitize_csv_value('+1234') == "'+1234"

    def test_minus_sign_prefixed(self):
        assert _sanitize_csv_value('-1234') == "'-1234"

    def test_at_sign_prefixed(self):
        assert _sanitize_csv_value('@SUM(A1)') == "'@SUM(A1)"

    def test_tab_prefixed(self):
        assert _sanitize_csv_value('\tcmd') == "'\tcmd"

    def test_carriage_return_prefixed(self):
        assert _sanitize_csv_value('\rcmd') == "'\rcmd"

    def test_empty_string_unchanged(self):
        assert _sanitize_csv_value('') == ''


# ── JWT Token Edge Cases ─────────────────────────────────────────

class TestJWTEdgeCases:
    def test_create_and_decode_roundtrip(self):
        token = create_token(42, 'testuser')
        payload = decode_token(token)
        assert payload is not None
        assert payload['user_id'] == 42
        assert payload['username'] == 'testuser'

    def test_decode_garbage_returns_none(self):
        assert decode_token('not.a.valid.token') is None

    def test_decode_empty_string_returns_none(self):
        assert decode_token('') is None

    def test_token_contains_expected_claims(self):
        token = create_token(1, 'user')
        payload = decode_token(token)
        assert 'exp' in payload
        assert 'iat' in payload
        assert 'user_id' in payload
        assert 'username' in payload


# ── API Age Validation ───────────────────────────────────────────

class TestAPIAgeValidation:
    def test_age_too_young_rejected(self, client):
        resp = client.post('/api/register',
                           data=json.dumps({
                               'username': 'young', 'password': 'StrongP@ss1',
                               'age': '10', 'address': '123 St',
                               'email': 'test@example.com'
                           }),
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'Age must be between 16 and 120' in resp.get_json()['error']

    def test_age_too_old_rejected(self, client):
        resp = client.post('/api/register',
                           data=json.dumps({
                               'username': 'old', 'password': 'StrongP@ss1',
                               'age': '200', 'address': '123 St',
                               'email': 'test@example.com'
                           }),
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'Age must be between 16 and 120' in resp.get_json()['error']

    def test_age_non_numeric_rejected(self, client):
        resp = client.post('/api/register',
                           data=json.dumps({
                               'username': 'bad', 'password': 'StrongP@ss1',
                               'age': 'abc', 'address': '123 St',
                               'email': 'test@example.com'
                           }),
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'Age must be a valid number' in resp.get_json()['error']

    def test_age_boundary_16_accepted(self, client):
        """Age 16 should pass validation (may fail on duplicate user, but not on age)."""
        with patch('application.routes.api_routes.find_by_username', return_value=None), \
             patch('application.routes.api_routes.register_user'), \
             patch('application.routes.api_routes.create_user_profile'), \
             patch('application.routes.api_routes.log_data_create'), \
             patch('application.routes.api_routes.log_login_success'), \
             patch('application.routes.api_routes.create_token', return_value='tok'), \
             patch('application.routes.api_routes.find_by_username', side_effect=[None, (99, 'hash')]):
            resp = client.post('/api/register',
                               data=json.dumps({
                                   'username': 'edgeuser', 'password': 'StrongP@ss1',
                                   'age': '16', 'address': '123 St',
                                   'email': 'edge@example.com'
                               }),
                               content_type='application/json')
            # Should not fail with age error
            assert 'Age must' not in resp.get_json().get('error', '')


# ── Audit Dashboard Date Range Bad Input ─────────────────────────

class TestDateRangeBadInput:
    def test_non_numeric_date_range_does_not_crash(self, auditor_client):
        """A non-numeric date_range should fall back to the default, not raise a 500."""
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]), \
             patch('application.routes.admin_routes.get_audit_log_count', return_value=0), \
             patch('application.routes.admin_routes.get_action_summary', return_value={}), \
             patch('application.routes.admin_routes.verify_audit_chain', return_value=True), \
             patch('application.routes.admin_routes.render_template', return_value='ok'), \
             patch('application.services.audit_service.insert_audit_log', return_value=1):
            resp = auditor_client.get('/admin/?date_range=abc')
            assert resp.status_code == 200

    def test_empty_date_range_does_not_crash(self, auditor_client):
        with patch('application.routes.admin_routes.get_audit_logs', return_value=[]), \
             patch('application.routes.admin_routes.get_audit_log_count', return_value=0), \
             patch('application.routes.admin_routes.get_action_summary', return_value={}), \
             patch('application.routes.admin_routes.verify_audit_chain', return_value=True), \
             patch('application.routes.admin_routes.render_template', return_value='ok'), \
             patch('application.services.audit_service.insert_audit_log', return_value=1):
            resp = auditor_client.get('/admin/?date_range=')
            assert resp.status_code == 200


# ── Audit Hash Chain ─────────────────────────────────────────────

class TestAuditHashChain:
    def test_compute_hash_deterministic(self):
        """Same inputs must always produce the same hash."""
        h1 = compute_hash('2025-01-01T00:00:00', 1, 'user', 'login',
                          'users', 1, '127.0.0.1', None, 'GENESIS')
        h2 = compute_hash('2025-01-01T00:00:00', 1, 'user', 'login',
                          'users', 1, '127.0.0.1', None, 'GENESIS')
        assert h1 == h2

    def test_compute_hash_changes_with_different_action(self):
        h1 = compute_hash('2025-01-01T00:00:00', 1, 'user', 'login',
                          'users', 1, '127.0.0.1', None, 'GENESIS')
        h2 = compute_hash('2025-01-01T00:00:00', 1, 'user', 'logout',
                          'users', 1, '127.0.0.1', None, 'GENESIS')
        assert h1 != h2

    def test_compute_hash_with_details_dict(self):
        """Details dict should be serialised consistently."""
        h1 = compute_hash('2025-01-01T00:00:00', 1, 'user', 'login',
                          'users', 1, '127.0.0.1', {'b': 2, 'a': 1}, 'GENESIS')
        h2 = compute_hash('2025-01-01T00:00:00', 1, 'user', 'login',
                          'users', 1, '127.0.0.1', {'a': 1, 'b': 2}, 'GENESIS')
        assert h1 == h2  # sort_keys=True ensures consistent ordering

    def test_hash_is_64_char_hex(self):
        h = compute_hash('ts', 1, 'user', 'login', 'users', 1, None, None, 'GENESIS')
        assert len(h) == 64
        assert all(c in '0123456789abcdef' for c in h)
