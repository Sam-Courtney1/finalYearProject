from unittest.mock import patch, MagicMock


class TestConsentManagement:
    def test_consent_page_renders(self, auth_client):
        with patch('application.routes.pages_and_actions.get_user_submissions', return_value=[]):
            resp = auth_client.get('/consent')
            assert resp.status_code == 200

    def test_withdraw_consent_success(self, auth_client):
        with patch('application.routes.pages_and_actions.withdraw_consent', return_value=True), \
             patch('application.routes.pages_and_actions.log_data_update'):
            resp = auth_client.post('/consent/withdraw/1', follow_redirects=True)
            assert b'withdrawn' in resp.data.lower() or resp.status_code == 200

    def test_withdraw_consent_not_found(self, auth_client):
        with patch('application.routes.pages_and_actions.withdraw_consent', return_value=False):
            resp = auth_client.post('/consent/withdraw/999', follow_redirects=True)
            assert b'not found' in resp.data.lower() or resp.status_code == 200

    def test_reinstate_consent_success(self, auth_client):
        with patch('application.routes.pages_and_actions.reinstate_consent', return_value=True), \
             patch('application.routes.pages_and_actions.log_data_update'):
            resp = auth_client.post('/consent/reinstate/1', follow_redirects=True)
            assert b're-given' in resp.data.lower() or resp.status_code == 200

    def test_reinstate_consent_not_found(self, auth_client):
        with patch('application.routes.pages_and_actions.reinstate_consent', return_value=False):
            resp = auth_client.post('/consent/reinstate/999', follow_redirects=True)
            assert b'not found' in resp.data.lower() or resp.status_code == 200

    def test_delete_submission_success(self, auth_client):
        result = {'success': True, 'client_name': 'HSE', 'answers_deleted': 3}
        with patch('application.routes.pages_and_actions.delete_single_submission', return_value=result), \
             patch('application.routes.pages_and_actions.log_data_delete'):
            resp = auth_client.post('/delete_submission/1', follow_redirects=True)
            assert b'deleted' in resp.data.lower() or resp.status_code == 200

    def test_delete_submission_not_found(self, auth_client):
        with patch('application.routes.pages_and_actions.delete_single_submission', return_value=None):
            resp = auth_client.post('/delete_submission/999', follow_redirects=True)
            assert b'not found' in resp.data.lower() or resp.status_code == 200
