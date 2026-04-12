from unittest.mock import patch, MagicMock


class TestForgotPassword:
    def test_forgot_password_page_renders(self, client):
        resp = client.get('/forgot-password')
        assert resp.status_code == 200

    def test_forgot_password_always_shows_same_message(self, client):
        """Prevents username enumeration, same flash whether user exists or not."""
        with patch('application.routes.pages_and_actions.find_by_username', return_value=None):
            resp = client.post('/forgot-password', data={'username': 'nonexistent'}, follow_redirects=True)
            assert b'If that account exists' in resp.data

    def test_forgot_password_with_valid_user_sends_email(self, client):
        mock_user = (1, 'hashed_pw')
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = ('user@test.com',)

        with patch('application.routes.pages_and_actions.find_by_username', return_value=mock_user), \
             patch('application.routes.pages_and_actions.get_db') as mock_db, \
             patch('application.routes.pages_and_actions.generate_reset_token', return_value='tok123'), \
             patch('application.routes.pages_and_actions.store_reset_token'), \
             patch('application.routes.pages_and_actions.send_password_reset_email') as mock_send:
            mock_db.return_value.__enter__ = MagicMock(return_value=(MagicMock(), mock_cur))
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            resp = client.post('/forgot-password', data={'username': 'realuser'}, follow_redirects=True)
            mock_send.assert_called_once()


class TestResetPassword:
    def test_reset_page_with_invalid_token_redirects(self, client):
        with patch('application.routes.pages_and_actions.verify_reset_token', return_value=None):
            resp = client.get('/reset-password/badtoken', follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_reset_page_with_valid_token_renders(self, client):
        with patch('application.routes.pages_and_actions.verify_reset_token', return_value=1):
            resp = client.get('/reset-password/goodtoken')
            assert resp.status_code == 200

    def test_reset_password_weak_password_rejected(self, client):
        with patch('application.routes.pages_and_actions.verify_reset_token', return_value=1):
            resp = client.post('/reset-password/goodtoken', data={
                'password': 'weak',
                'confirm_password': 'weak'
            }, follow_redirects=True)
            assert b'Password must' in resp.data

    def test_reset_password_mismatched_passwords_rejected(self, client):
        with patch('application.routes.pages_and_actions.verify_reset_token', return_value=1):
            resp = client.post('/reset-password/goodtoken', data={
                'password': 'StrongPass1!',
                'confirm_password': 'Different1!'
            }, follow_redirects=True)
            assert b'do not match' in resp.data
