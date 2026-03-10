from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash


class TestRightToAccess:
    """GDPR Article 15 - Right of access by the data subject."""

    def test_access_data_renders_for_logged_in_user(self, auth_client):
        """Authenticated users should see their data."""
        with patch('application.routes.pages_and_actions.get_user_data',
                   return_value=([], [])):
            resp = auth_client.get('/right_to_access')
            assert resp.status_code == 200

    def test_access_data_requires_login(self, client):
        """Unauthenticated users should be redirected to login."""
        resp = client.get('/right_to_access', follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestRightToErasure:
    """GDPR Article 17 - Right to erasure ('right to be forgotten')."""

    def test_delete_account_calls_delete_user(self, auth_client):
        """Account deletion should call delete_user with the correct user_id."""
        hashed = generate_password_hash('TestPass1!')
        with patch('application.routes.pages_and_actions.find_by_id', return_value=(1, hashed)), \
             patch('application.routes.pages_and_actions.delete_user') as mock_delete, \
             patch('application.routes.pages_and_actions.log_data_delete'):
            resp = auth_client.post('/right_to_forget', data={
                'password': 'TestPass1!'
            }, follow_redirects=True)
            mock_delete.assert_called_once_with(1)

    def test_delete_account_wrong_password_rejected(self, auth_client):
        """Wrong password should not allow deletion."""
        hashed = generate_password_hash('CorrectPass1!')
        with patch('application.routes.pages_and_actions.find_by_id', return_value=(1, hashed)), \
             patch('application.routes.pages_and_actions.delete_user') as mock_delete:
            resp = auth_client.post('/right_to_forget', data={
                'password': 'WrongPass1!'
            }, follow_redirects=True)
            mock_delete.assert_not_called()

    def test_delete_account_requires_login(self, client):
        """Unauthenticated deletion should redirect."""
        resp = client.post('/right_to_forget', data={'password': 'x'}, follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_delete_data_only_preserves_account(self, auth_client):
        """Data-only deletion should call delete_user_data_only, not delete_user."""
        with patch('application.routes.pages_and_actions.delete_user_data_only') as mock_data_del, \
             patch('application.routes.pages_and_actions.delete_user') as mock_acct_del, \
             patch('application.routes.pages_and_actions.log_data_delete'):
            resp = auth_client.post('/delete_user_data', follow_redirects=True)
            mock_data_del.assert_called_once_with(1)
            mock_acct_del.assert_not_called()


class TestDataPortability:
    """GDPR Article 20 - Right to data portability."""

    def test_export_returns_csv(self, auth_client):
        """Data export should return a CSV file."""
        with patch('application.routes.pages_and_actions.get_user_data',
                   return_value=([], [])), \
             patch('application.routes.pages_and_actions.log_data_export'):
            resp = auth_client.get('/export_data')
            assert resp.status_code == 200
            assert 'text/csv' in resp.content_type


class TestSessionTimeout:
    """Server-side session timeout enforcement (10-minute inactivity)."""

    def test_expired_session_redirects_to_login(self, app):
        """A session with last_activity > 10 minutes ago should be cleared."""
        import time
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
                # Set last_activity to 11 minutes ago
                sess['last_activity'] = time.time() - 660

            resp = c.get('/homepage', follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_active_session_is_not_cleared(self, auth_client):
        """A session with recent activity should remain active."""
        resp = auth_client.get('/homepage')
        assert resp.status_code == 200
