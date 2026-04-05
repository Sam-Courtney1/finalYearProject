"""
Shared consent validation used by both the web questionnaire routes
and the mobile API routes to ensure consistent consent checking.
"""


def validate_consent(form_data):
    """Check that explicit consent was given in the submitted form data.

    Parameters:
        form_data: dict-like object (request.form or parsed JSON body)

    Returns:
        (True, None) if consent is present, or (False, error_message) if not.
    """
    consent_value = form_data.get('consent')
    if consent_value in (True, 'on', 'true', '1'):
        return True, None
    return False, "Consent is required to submit a questionnaire."
