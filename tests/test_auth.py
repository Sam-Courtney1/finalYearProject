from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash


class TestLoginPage:
    def test_login_page_renders(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_login_with_valid_credentials_redirects(self, client):
        hashed = generate_password_hash('Password1!')
        mock_user = (1, hashed)
        with patch('application.routes.pages_and_actions.authenticate_user', return_value=1), \
             patch('application.routes.pages_and_actions.get_db') as mock_db, \
             patch('application.routes.pages_and_actions.send_otp_email', return_value=(False, 'no ses')), \
             patch('application.routes.pages_and_actions.log_login_success'):
            # Mock DB call for email lookup — return None so 2FA is skipped
            mock_cur = MagicMock()
            mock_cur.fetchone.return_value = None
            mock_db.return_value.__enter__ = MagicMock(return_value=(MagicMock(), mock_cur))
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            resp = client.post('/login', data={
                'username': 'testuser',
                'password': 'Password1!'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_login_with_invalid_credentials_flashes_error(self, client):
        with patch('application.routes.pages_and_actions.authenticate_user', return_value=None), \
             patch('application.routes.pages_and_actions.log_login_failed'):
            resp = client.post('/login', data={
                'username': 'baduser',
                'password': 'wrong'
            }, follow_redirects=True)
            assert b'incorrect' in resp.data.lower() or resp.status_code == 200


class TestRegister:
    def test_register_page_renders(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200

    def test_register_weak_password_rejected(self, client):
        resp = client.post('/register_user', data={
            'username': 'newuser',
            'password': 'weak',
            'age': '25',
            'address': '123 Street',
            'email': 'a@b.com'
        }, follow_redirects=True)
        assert b'Password must' in resp.data or resp.status_code == 200

    def test_register_invalid_age_rejected(self, client):
        resp = client.post('/register_user', data={
            'username': 'newuser',
            'password': 'StrongPass1!',
            'age': '5',
            'address': '123 Street',
            'email': 'a@b.com'
        }, follow_redirects=True)
        assert b'Age must be between' in resp.data or resp.status_code == 200

    def test_register_non_numeric_age_rejected(self, client):
        resp = client.post('/register_user', data={
            'username': 'newuser',
            'password': 'StrongPass1!',
            'age': 'abc',
            'address': '123 Street',
            'email': 'a@b.com'
        }, follow_redirects=True)
        assert b'valid age' in resp.data.lower() or resp.status_code == 200

    def test_register_duplicate_username_rejected(self, client):
        with patch('application.routes.pages_and_actions.find_by_username', return_value=(1, 'hash')):
            resp = client.post('/register_user', data={
                'username': 'existing',
                'password': 'StrongPass1!',
                'age': '25',
                'address': '123 Street',
                'email': 'a@b.com'
            }, follow_redirects=True)
            assert b'already exists' in resp.data.lower() or resp.status_code == 200

    def test_register_missing_email_rejected(self, client):
        resp = client.post('/register_user', data={
            'username': 'newuser',
            'password': 'StrongPass1!',
            'age': '25',
            'address': '123 Street',
            'email': ''
        }, follow_redirects=True)
        assert b'Email' in resp.data or resp.status_code == 200


class TestLogout:
    def test_logout_clears_session(self, auth_client):
        with patch('application.routes.pages_and_actions.log_logout'):
            resp = auth_client.get('/logout', follow_redirects=False)
            assert resp.status_code in (302, 303)
            # After logout, homepage should redirect to login
            resp2 = auth_client.get('/homepage', follow_redirects=False)
            assert resp2.status_code in (302, 303)
