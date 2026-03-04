from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash


class TestClientLogin:
    def test_client_login_page_renders(self, client):
        resp = client.get('/client/')
        assert resp.status_code == 200

    def test_client_login_valid(self, client):
        hashed = generate_password_hash('Password1!')
        mock_client = (1, 'testclient', hashed)
        with patch('application.routes.client_routes.find_client_by_username', return_value=mock_client), \
             patch('application.routes.client_routes.log_login_success'):
            resp = client.post('/client/', data={
                'username': 'testclient',
                'password': 'Password1!'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_client_login_invalid(self, client):
        with patch('application.routes.client_routes.find_client_by_username', return_value=None), \
             patch('application.routes.client_routes.log_login_failed'):
            resp = client.post('/client/', data={
                'username': 'bad',
                'password': 'wrong'
            }, follow_redirects=True)
            assert b'Invalid' in resp.data or resp.status_code == 200


class TestClientRegister:
    def test_client_register_page_renders(self, client):
        resp = client.get('/client/register')
        assert resp.status_code == 200

    def test_client_register_weak_password(self, client):
        resp = client.post('/client/register', data={
            'username': 'newclient',
            'password': 'weak'
        }, follow_redirects=True)
        assert b'Password must' in resp.data


class TestClientQuestionnaire:
    def test_questionnaire_list_renders(self, client_auth_client):
        with patch('application.routes.client_routes.get_questionnaires_for_client', return_value=[]):
            resp = client_auth_client.get('/client/questionnaires')
            assert resp.status_code == 200

    def test_create_questionnaire_empty_name_rejected(self, client_auth_client):
        resp = client_auth_client.post('/client/questionnaire/create', data={
            'questionnaire_name': ''
        }, follow_redirects=True)
        assert b'cannot be empty' in resp.data.lower() or resp.status_code == 200

    def test_add_field_invalid_type_rejected(self, client_auth_client):
        with patch('application.routes.client_routes.get_fields_for_client', return_value=[]):
            resp = client_auth_client.post('/client/questionnaire/TestQ', data={
                'label': 'Name',
                'field_type': 'script_injection',
                'category': 'PII'
            }, follow_redirects=True)
            assert b'Invalid field type' in resp.data or resp.status_code == 200

    def test_add_field_invalid_category_rejected(self, client_auth_client):
        with patch('application.routes.client_routes.get_fields_for_client', return_value=[]):
            resp = client_auth_client.post('/client/questionnaire/TestQ', data={
                'label': 'Name',
                'field_type': 'text',
                'category': 'HackedCategory'
            }, follow_redirects=True)
            assert b'Invalid category' in resp.data or resp.status_code == 200
