"""
Tests that all protected routes redirect unauthenticated users to login.
"""

class TestUserRoutesRequireLogin:
    """Every route with @require_user_login should 302 to login when not authenticated."""

    def test_homepage_redirects(self, client):
        resp = client.get('/homepage', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_right_to_access_redirects(self, client):
        resp = client.get('/right_to_access', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_consent_redirects(self, client):
        resp = client.get('/consent', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_export_data_redirects(self, client):
        resp = client.get('/export_data', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_select_questionnaire_redirects(self, client):
        resp = client.get('/questionnaire', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_edit_select_redirects(self, client):
        resp = client.get('/edit', follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestClientRoutesRequireLogin:
    """Every route with @require_client_login should 302 to client login when not authenticated."""

    def test_client_dashboard_redirects(self, client):
        resp = client.get('/client/dashboard', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_client_questionnaire_list_redirects(self, client):
        resp = client.get('/client/questionnaires', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_admin_dashboard_redirects(self, client):
        resp = client.get('/admin/', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_admin_export_redirects(self, client):
        resp = client.get('/admin/export', follow_redirects=False)
        assert resp.status_code in (302, 303)
