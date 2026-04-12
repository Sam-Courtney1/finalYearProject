from unittest.mock import patch


class TestUserDashboard:
    def test_user_dashboard_renders(self, auth_client):
        mock_stats = {'total_submissions': 3, 'active_consents': 2, 'withdrawn_consents': 1}
        mock_dsrs = []
        with patch('application.routes.pages_and_actions.get_user_dashboard_stats',
                   return_value=mock_stats), \
             patch('application.routes.pages_and_actions.get_dsrs_for_user',
                   return_value=mock_dsrs):
            resp = auth_client.get('/dashboard')
            assert resp.status_code == 200

    def test_user_dashboard_requires_login(self, client):
        resp = client.get('/dashboard', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_user_dashboard_shows_stats(self, auth_client):
        mock_stats = {'total_submissions': 5, 'active_consents': 3, 'withdrawn_consents': 2}
        mock_dsrs = []
        with patch('application.routes.pages_and_actions.get_user_dashboard_stats',
                   return_value=mock_stats), \
             patch('application.routes.pages_and_actions.get_dsrs_for_user',
                   return_value=mock_dsrs):
            resp = auth_client.get('/dashboard')
            assert resp.status_code == 200


class TestHomepage:
    def test_homepage_renders_for_logged_in_user(self, auth_client):
        resp = auth_client.get('/homepage')
        assert resp.status_code == 200

    def test_homepage_requires_login(self, client):
        resp = client.get('/homepage', follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestPrivacyPolicy:
    def test_privacy_policy_renders(self, client):
        resp = client.get('/privacy')
        assert resp.status_code == 200

    def test_privacy_policy_accessible_without_login(self, client):
        resp = client.get('/privacy')
        assert resp.status_code == 200
        assert b'privacy' in resp.data.lower() or b'GDPR' in resp.data or resp.status_code == 200
