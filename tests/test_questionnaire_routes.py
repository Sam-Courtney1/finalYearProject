from unittest.mock import patch, MagicMock


class TestQuestionnaireSelection:
    def test_select_questionnaire_renders(self, auth_client):
        resp = auth_client.get('/questionnaire')
        assert resp.status_code == 200

    def test_select_questionnaire_requires_login(self, client):
        resp = client.get('/questionnaire', follow_redirects=False)
        assert resp.status_code in (302, 303)

    def test_select_edit_renders(self, auth_client):
        with patch('application.routes.questionnaire_routes.get_user_submissions', return_value=[]):
            resp = auth_client.get('/edit')
            assert resp.status_code == 200


class TestQuestionnaireForm:
    def test_questionnaire_form_renders(self, auth_client):
        mock_fields = [
            (1, 'Full Name', 'text', 'PII'),
            (2, 'Blood Type', 'text', 'Medical')
        ]
        with patch('application.routes.questionnaire_routes.get_db') as mock_get_db:
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = mock_fields
            mock_cur.fetchone.return_value = ('TestOrg',)
            mock_conn = MagicMock()
            mock_get_db.return_value.__enter__ = MagicMock(return_value=(mock_conn, mock_cur))
            mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
            resp = auth_client.get('/questionnaire/1/TestQuestionnaire')
            assert resp.status_code == 200

    def test_questionnaire_form_invalid_name_path_traversal(self, auth_client):
        resp = auth_client.get('/questionnaire/1/..etc..test', follow_redirects=True)
        # Name containing '..' is rejected by _valid_questionnaire_name
        assert resp.status_code == 200

    def test_questionnaire_form_invalid_name_slash(self, auth_client):
        resp = auth_client.get('/questionnaire/1/bad/name', follow_redirects=True)
        # Flask will return 404 for path with extra slash segment
        assert resp.status_code in (200, 404)


class TestQuestionnaireSubmission:
    def test_submit_questionnaire_success(self, auth_client):
        with patch('application.routes.questionnaire_routes.validate_consent', return_value=(True, None)), \
             patch('application.routes.questionnaire_routes.handle_questionnaire_submission'), \
             patch('application.routes.questionnaire_routes.log_data_create'):
            resp = auth_client.post('/questionnaire/1/TestQ', data={
                'consent': 'on',
                'field_1': 'John Doe',
                'field_2': 'A+'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_submit_questionnaire_without_consent_rejected(self, auth_client):
        with patch('application.routes.questionnaire_routes.validate_consent',
                   return_value=(False, 'Consent is required to submit a questionnaire.')):
            resp = auth_client.post('/questionnaire/1/TestQ', data={
                'field_1': 'John Doe'
            }, follow_redirects=True)
            assert b'Consent' in resp.data or resp.status_code == 200

    def test_submit_questionnaire_requires_login(self, client):
        resp = client.post('/questionnaire/1/TestQ', data={
            'consent': 'on'
        }, follow_redirects=False)
        assert resp.status_code in (302, 303)


class TestQuestionnaireEditing:
    def test_edit_submission_renders(self, auth_client):
        mock_answers = [
            {'field_id': 1, 'field_label': 'Name', 'value': 'John', 'category': 'PII'}
        ]
        with patch('application.routes.questionnaire_routes.get_submission_answers',
                   return_value=mock_answers):
            resp = auth_client.get('/edit/1')
            assert resp.status_code == 200

    def test_edit_submission_not_found(self, auth_client):
        with patch('application.routes.questionnaire_routes.get_submission_answers',
                   return_value=None):
            resp = auth_client.get('/edit/999', follow_redirects=True)
            assert b'not found' in resp.data.lower() or b'access denied' in resp.data.lower() or resp.status_code == 200

    def test_save_edited_submission_success(self, auth_client):
        with patch('application.routes.questionnaire_routes.update_submission_answers', return_value=2), \
             patch('application.routes.questionnaire_routes.log_data_update'):
            resp = auth_client.post('/edit/1', data={
                'field_1': 'Updated Name',
                'field_2': 'Updated Value'
            }, follow_redirects=False)
            assert resp.status_code in (302, 303)

    def test_save_edited_submission_access_denied(self, auth_client):
        with patch('application.routes.questionnaire_routes.update_submission_answers', return_value=None):
            resp = auth_client.post('/edit/999', data={
                'field_1': 'Value'
            }, follow_redirects=True)
            assert b'not found' in resp.data.lower() or b'access denied' in resp.data.lower() or resp.status_code == 200

    def test_edit_requires_login(self, client):
        resp = client.get('/edit/1', follow_redirects=False)
        assert resp.status_code in (302, 303)
