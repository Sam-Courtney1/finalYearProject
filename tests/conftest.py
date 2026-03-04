import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager


@contextmanager
def mock_db_context():
    """Yields a fake (conn, cur) pair for mocking get_db()."""
    conn = MagicMock()
    cur = MagicMock()
    yield conn, cur


@pytest.fixture()
def app():
    """Create a Flask test app with all DB-touching startup code mocked out."""
    with patch('data.audit_database.create_audit_table'), \
         patch('data.migrations.run_migrations'), \
         patch('data.db_connection.get_db', side_effect=mock_db_context):
        from wsgi import create_app
        test_app = create_app()
        test_app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,   # Disable CSRF for test convenience
            'SECRET_KEY': 'test-secret',
        })
        yield test_app


@pytest.fixture()
def client(app):
    """Unauthenticated Flask test client."""
    return app.test_client()


@pytest.fixture()
def auth_client(app):
    """Flask test client with a logged-in regular user session."""
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['last_activity'] = __import__('time').time()
        yield c


@pytest.fixture()
def client_auth_client(app):
    """Flask test client with a logged-in client/organisation session."""
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['client_id'] = 1
            sess['client_username'] = 'testclient'
        yield c
