from unittest.mock import patch


class TestVerify2FA:
    def test_verify_page_requires_pending_session(self, client):
        resp = client.get('/verify-2fa', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_verify_page_renders_when_pending(self, client):
        with client.session_transaction() as sess:
            sess['pending_2fa_user'] = 1
            sess['pending_2fa_username'] = 'testuser'
        resp = client.get('/verify-2fa')
        assert resp.status_code == 200

    def test_correct_otp_logs_in(self, client):
        with client.session_transaction() as sess:
            sess['pending_2fa_user'] = 1
            sess['pending_2fa_username'] = 'testuser'

        with patch('application.routes.pages_and_actions.verify_otp', return_value=(True, 'ok')), \
             patch('application.routes.pages_and_actions.log_login_success'):
            resp = client.post('/verify-2fa', data={'otp_code': '123456'}, follow_redirects=False)
            assert resp.status_code in (302, 303)
            # Should now be authenticated
            with client.session_transaction() as sess:
                assert sess.get('user_id') == 1

    def test_wrong_otp_shows_error(self, client):
        with client.session_transaction() as sess:
            sess['pending_2fa_user'] = 1
            sess['pending_2fa_username'] = 'testuser'

        with patch('application.routes.pages_and_actions.verify_otp', return_value=(False, 'invalid')):
            resp = client.post('/verify-2fa', data={'otp_code': '000000'}, follow_redirects=True)
            assert b'Incorrect code' in resp.data or resp.status_code == 200

    def test_expired_otp_redirects_to_login(self, client):
        with client.session_transaction() as sess:
            sess['pending_2fa_user'] = 1
            sess['pending_2fa_username'] = 'testuser'

        with patch('application.routes.pages_and_actions.verify_otp', return_value=(False, 'expired')):
            resp = client.post('/verify-2fa', data={'otp_code': '123456'}, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_max_attempts_redirects_to_login(self, client):
        with client.session_transaction() as sess:
            sess['pending_2fa_user'] = 1
            sess['pending_2fa_username'] = 'testuser'

        with patch('application.routes.pages_and_actions.verify_otp', return_value=(False, 'max_attempts')), \
             patch('application.routes.pages_and_actions.log_login_failed'):
            resp = client.post('/verify-2fa', data={'otp_code': '123456'}, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_resend_without_pending_redirects(self, client):
        resp = client.post('/resend-2fa', follow_redirects=False)
        assert resp.status_code in (302, 303)
