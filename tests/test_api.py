import json
from unittest.mock import patch, MagicMock


def auth_header(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


class TestAPIAuth:
    def test_login_missing_body_returns_400(self, client):
        resp = client.post('/api/login', content_type='application/json')
        assert resp.status_code == 400

    def test_login_valid_credentials(self, client):
        with patch('application.routes.api_routes.authenticate_user', return_value=1), \
             patch('application.routes.api_routes.log_login_success'), \
             patch('application.routes.api_routes.create_token', return_value='tok123'):
            resp = client.post('/api/login',
                               data=json.dumps({'username': 'user', 'password': 'Pass1!aa'}),
                               content_type='application/json')
            assert resp.status_code == 200
            data = resp.get_json()
            assert data['token'] == 'tok123'

    def test_login_invalid_credentials(self, client):
        with patch('application.routes.api_routes.authenticate_user', return_value=None), \
             patch('application.routes.api_routes.log_login_failed'):
            resp = client.post('/api/login',
                               data=json.dumps({'username': 'bad', 'password': 'wrong'}),
                               content_type='application/json')
            assert resp.status_code == 401

    def test_register_weak_password_rejected(self, client):
        resp = client.post('/api/register',
                           data=json.dumps({
                               'username': 'new', 'password': 'weak',
                               'age': '25', 'address': '123 St',
                               'email': 'test@example.com'
                           }),
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'Password must' in resp.get_json()['error']


class TestAPIProtectedRoutes:
    def test_no_token_returns_401(self, client):
        resp = client.get('/api/user/data')
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get('/api/user/data', headers=auth_header('invalidtoken'))
        assert resp.status_code == 401

    def test_valid_token_accesses_data(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.get_user_data', return_value=([], [])):
            resp = client.get('/api/user/data', headers=auth_header('goodtoken'))
            assert resp.status_code == 200

    def test_delete_account(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.delete_user'), \
             patch('application.routes.api_routes.log_data_delete'):
            resp = client.delete('/api/user/account', headers=auth_header('goodtoken'))
            assert resp.status_code == 200

    def test_delete_data_only(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.delete_user_data_only'), \
             patch('application.routes.api_routes.log_data_delete'):
            resp = client.delete('/api/user/data', headers=auth_header('goodtoken'))
            assert resp.status_code == 200

    def test_list_submissions(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.get_user_submissions', return_value=[]):
            resp = client.get('/api/submissions', headers=auth_header('goodtoken'))
            assert resp.status_code == 200
            assert 'submissions' in resp.get_json()

    def test_list_clients_and_questionnaires(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}):
            resp = client.get('/api/clients', headers=auth_header('goodtoken'))
            assert resp.status_code == 200

    def test_withdraw_consent_via_api(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.withdraw_consent', return_value=True), \
             patch('application.routes.api_routes.log_data_update'):
            resp = client.post('/api/submissions/1/consent/withdraw',
                               headers=auth_header('goodtoken'))
            assert resp.status_code == 200

    def test_reinstate_consent_via_api(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.reinstate_consent', return_value=True), \
             patch('application.routes.api_routes.log_data_update'):
            resp = client.post('/api/submissions/1/consent/reinstate',
                               headers=auth_header('goodtoken'))
            assert resp.status_code == 200

    def test_consent_withdraw_not_found(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.withdraw_consent', return_value=False):
            resp = client.post('/api/submissions/999/consent/withdraw',
                               headers=auth_header('goodtoken'))
            assert resp.status_code == 404

    def test_get_submission_answers(self, client):
        mock_answers = [(1, 'Name', 'text', 'PII', 'John')]
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.get_submission_answers', return_value=mock_answers):
            resp = client.get('/api/submissions/1/answers', headers=auth_header('goodtoken'))
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data['fields']) == 1

    def test_get_submission_answers_not_found(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.get_submission_answers', return_value=None):
            resp = client.get('/api/submissions/999/answers', headers=auth_header('goodtoken'))
            assert resp.status_code == 404

    def test_dsr_history(self, client):
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.get_dsrs_for_user', return_value=[]):
            resp = client.get('/api/dsr', headers=auth_header('goodtoken'))
            assert resp.status_code == 200
            assert 'data_subject_requests' in resp.get_json()

    def test_user_dashboard_api(self, client):
        mock_stats = {
            'total_submissions': 2, 'total_organisations': 1,
            'active_consents': 2, 'withdrawn_consents': 0, 'submissions': []
        }
        with patch('application.routes.api_routes.decode_token', return_value={'user_id': 1, 'username': 'u'}), \
             patch('application.routes.api_routes.get_user_dashboard_stats', return_value=mock_stats), \
             patch('application.routes.api_routes.get_dsrs_for_user', return_value=[]):
            resp = client.get('/api/dashboard', headers=auth_header('goodtoken'))
            assert resp.status_code == 200
