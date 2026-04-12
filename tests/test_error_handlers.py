class TestErrorHandlers:
    def test_404_returns_error_page(self, client):
        resp = client.get('/this-page-does-not-exist')
        assert resp.status_code == 404

    def test_404_contains_error_message(self, client):
        resp = client.get('/nonexistent-route-xyz')
        assert resp.status_code == 404
        assert b'404' in resp.data or b'not found' in resp.data.lower()


class TestHealthCheck:
    def test_health_check_returns_healthy(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'healthy'

    def test_health_check_returns_json(self, client):
        resp = client.get('/health')
        assert resp.content_type.startswith('application/json')
