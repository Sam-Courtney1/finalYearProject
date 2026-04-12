import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager


@contextmanager
def mock_db_context():
    """Yields a fake (conn, cur) pair for mocking get_db()."""
    conn = MagicMock()
    cur = MagicMock()
    yield conn, cur


def _mock_get_db():
    """Returns the mock context manager, used to replace get_db everywhere."""
    return mock_db_context()


@pytest.fixture()
def app():
    """Create a Flask test app with all DB-touching startup code mocked out."""
    import data.db_connection as db_mod

    # Prevent _get_pool from ever connecting to the real database
    # by setting _pool to a MagicMock before any test runs
    original_pool = db_mod._pool
    db_mod._pool = MagicMock()

    with patch('data.audit_database.create_audit_table'), \
         patch('data.migrations.run_migrations'), \
         patch('data.db_connection.get_db', side_effect=mock_db_context), \
         patch('data.audit_database.insert_audit_log'), \
         patch('application.services.audit_service.insert_audit_log'):

        # Also patch get_db in every data module that imports it directly
        # This ensures mocks work even after module-level imports
        import data.dsr_database
        import data.submission_database
        import data.user_database
        import data.breach_database
        import data.breach_notification_database
        import data.retention_database
        import data.questionnaire_client
        import data.client_database

        data_modules = [
            data.dsr_database, data.submission_database,
            data.user_database, data.breach_database,
            data.breach_notification_database, data.retention_database,
            data.questionnaire_client, data.client_database,
        ]

        saved = {}
        for mod in data_modules:
            if hasattr(mod, 'get_db'):
                saved[mod] = mod.get_db
                mod.get_db = _mock_get_db

        from wsgi import create_app
        test_app = create_app()
        test_app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,   # Disable CSRF for test convenience
            'SECRET_KEY': 'test-secret',
        })
        yield test_app

        # Restore originals
        for mod, original in saved.items():
            mod.get_db = original
        db_mod._pool = original_pool


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


@pytest.fixture()
def auditor_client(app):
    """Flask test client with a logged-in external auditor session."""
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['auditor_id'] = 99
            sess['auditor_username'] = 'test_auditor'
        yield c
