# Organ Donation System

A GDPR-compliant organ donation platform built with Flask. All personal data is encrypted at rest using AES-256 via PostgreSQL's pgcrypto extension.

## Features

**User site:**
- Register and log in with email-based 2FA
- Password reset via email
- Fill organisation questionnaires with consent tracking
- Right to Access — view all stored personal data
- Right to Data Portability — export data as CSV
- Right to be Forgotten — delete account and all associated data
- Consent management — withdraw or reinstate consent per submission
- 10-minute inactivity auto-logout (client + server enforced)

**Client (organisation) site:**
- Register and log in as an organisation
- Build custom questionnaires with field types and categories (PII, Medical, Demographic)
- View submissions with decrypted data
- Audit dashboard with login history, geolocation, and data integrity verification

**Mobile app** (separate codebase in `mobile_app/`):
- React Native app with JWT authentication
- Access the same features via `/api/` endpoints

## Prerequisites

- Python 3.10+
- PostgreSQL with the `pgcrypto` extension enabled
- A Gmail account with an App Password (for 2FA/password reset emails)
- AWS account (for RDS and Elastic Beanstalk deployment)

## Setup

1. Clone the repository
2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your values
4. Ensure your PostgreSQL database is running and has pgcrypto enabled:
   ```sql
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   ```
5. Run the application:
   ```
   python wsgi.py
   ```
   The app runs on `http://localhost:5000` by default.

## Environment Variables

See `.env.example` for all required variables. Key ones:

| Variable | Description |
|----------|-------------|
| `DB_HOST` | PostgreSQL host (e.g. your RDS endpoint) |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `APP_ENC_KEY` | Encryption key for pgcrypto and Flask sessions |
| `SMTP_EMAIL` | Gmail address for sending 2FA/reset emails |
| `SMTP_PASSWORD` | Gmail App Password (16-char) |

## Architecture

```
wsgi.py                          # Flask entry point
application/
  routes/                        # Blueprint route files (controllers)
    pages_and_actions.py         # Auth, GDPR rights, 2FA, password reset
    questionnaire_routes.py      # Questionnaire fill/edit
    home_route.py                # Homepage
    client_routes.py             # Organisation management
    admin_routes.py              # Audit dashboard
    api_routes.py                # Mobile app JSON API
  services/                      # Business logic
    authentication.py            # Password hashing and verification
    audit_service.py             # Audit trail logging
    otp_service.py               # OTP and reset token generation
    email_service.py             # Email sending via SMTP
    jwt_utils.py                 # JWT for mobile API
    log_form_data.py             # Questionnaire submission processing
data/                            # Database layer (PostgreSQL)
  db_connection.py               # Connection management
  user_database.py               # User CRUD
  submission_database.py         # Submission/consent CRUD
  audit_database.py              # Audit log storage
  migrations.py                  # Schema migrations
presentation/
  templates/                     # Jinja2 HTML templates
  static/                        # CSS and JavaScript
```

## Deployment

Deployed to AWS Elastic Beanstalk. Configuration is in `.ebextensions/01_flask.config`.

```
eb deploy
```

## Requirements

See `requirements.txt` for the full list of Python dependencies.
