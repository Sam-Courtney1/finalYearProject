# GDPR-Compliant Organ Donation System

A full-stack organ donation data management system built for GDPR compliance. Organisations create questionnaires, users fill them out with encrypted data storage, and an audit dashboard tracks all data access.

## Stack

- **Backend:** Python 3.12, Flask 3.0, PostgreSQL (pgcrypto for field-level encryption)
- **Frontend:** Jinja2 templates, Bootstrap 5.3.3, custom CSS
- **Mobile:** React Native (Expo) with JWT authentication
- **Hosting:** AWS Elastic Beanstalk (gunicorn + nginx)
- **Email:** Gmail SMTP for 2FA OTP and password reset

## Project Structure

```
wsgi.py                          # Flask app factory + blueprint registration
application/
  routes/
    pages_and_actions.py         # User auth (login/register/2FA) + GDPR rights
    client_routes.py             # Organisation login + questionnaire management
    admin_routes.py              # Audit dashboard, breach, retention, DSR, compliance
    questionnaire_routes.py      # Questionnaire fill + edit
    api_routes.py                # Mobile app JSON API (JWT auth)
    home_route.py                # Homepage
  services/
    audit_service.py             # @audit_log decorator + hash-chained audit trail
    authentication.py            # Password hashing + validation
    otp_service.py               # 2FA OTP + password reset tokens (SHA-256 hashed)
    email_service.py             # SMTP email sending
    jwt_utils.py                 # JWT token create/decode for mobile API
    retention_service.py         # Data retention cleanup (GDPR Art. 5(1)(e))
    breach_service.py            # 72-hour breach deadline tracking
    breach_notification_service.py # Breach email notifications (GDPR Art. 34)
    dsr_service.py               # Data subject request tracking (GDPR Art. 12-23)
    compliance_service.py        # Aggregated GDPR compliance dashboard
    decorators.py                # @require_user_login, @require_client_login
    log_form_data.py             # Questionnaire submission processing + encryption
  extensions.py                  # Flask-Limiter instance
data/
  db_connection.py               # PostgreSQL connection + context manager
  migrations.py                  # Schema migrations (idempotent, IF NOT EXISTS)
  user_database.py               # User CRUD
  client_database.py             # Organisation CRUD
  questionnaire.py               # Questionnaire data operations
  questionnaire_client.py        # Organisation questionnaire field management
  submission_database.py         # Submission + consent + answer operations
  audit_database.py              # Audit log insert/query + hash chain verification
  breach_database.py             # Breach CRUD
  breach_notification_database.py
  dsr_database.py                # Data subject request CRUD
  retention_database.py          # Inactive user + expired submission queries
presentation/
  templates/                     # 29 Jinja2 templates (4 base + 25 pages)
  static/
    main.css                     # Single CSS file (~4000 lines)
    landing.js                   # User landing page animations
    client_landing.js            # Organisation landing page animations
mobile_app/                      # React Native (Expo) mobile client
  src/
    api/                         # Axios API client + endpoint modules
    context/AuthContext.js        # JWT auth state management
    screens/                     # 10 screens (Login, Home, Questionnaire, etc.)
    components/                  # Reusable components (MenuCard, LoadingScreen)
    theme/theme.js               # Design tokens
tests/                           # 78 pytest tests across 9 test files
```

## Prerequisites

- Python 3.10+
- PostgreSQL 14+ with the `pgcrypto` extension enabled
- Node.js 18+ (for mobile app only)

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd finalYearProject
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your database credentials and keys
```

Required variables: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `APP_ENC_KEY`

### 3. Set up the database

Connect to PostgreSQL and create the database with pgcrypto:

```sql
CREATE DATABASE organ_donation;
\c organ_donation
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

Then create the core tables (migrations handle the rest automatically on app startup):

```sql
CREATE TABLE users (
    id       SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE clients (
    client_id SERIAL PRIMARY KEY,
    username  VARCHAR(100) UNIQUE NOT NULL,
    password  VARCHAR(255) NOT NULL
);

CREATE TABLE questionnaire_fields (
    field_id   SERIAL PRIMARY KEY,
    client_id  INTEGER NOT NULL REFERENCES clients(client_id),
    field_label VARCHAR(255) NOT NULL,
    field_type  VARCHAR(50) NOT NULL,
    category    VARCHAR(50) NOT NULL
);

CREATE TABLE submissions (
    submission_id SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_id     INTEGER REFERENCES clients(client_id),
    consent       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pii (
    pii_id         SERIAL PRIMARY KEY,
    submission_id  INTEGER NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    first_name_enc BYTEA,
    address_enc    BYTEA
);

CREATE TABLE demographic_data (
    demo_id       SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    age           INTEGER
);

CREATE TABLE answers (
    answer_id     SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    field_id      INTEGER NOT NULL REFERENCES questionnaire_fields(field_id),
    value_enc     BYTEA,
    value_plain   TEXT,
    value_hashed  TEXT
);
```

Additional tables (audit_logs, otp_tokens, password_reset_tokens, data_breaches, data_subject_requests, auditors, breach_notifications) are created automatically by `data/migrations.py` on first startup.

### 4. Run the application

```bash
# Development
flask --app wsgi run --debug

# Or directly
python wsgi.py

# Production (Elastic Beanstalk uses this via Procfile)
gunicorn --bind 0.0.0.0:8000 --workers 3 wsgi:application
```

The app will be available at `http://localhost:5000`.

### 5. Run tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=application --cov=data --cov-report=term-missing

# Run a specific test file
pytest tests/test_auth.py -v
```

### 6. Mobile app (optional)

```bash
cd mobile_app
npm install
npx expo start
```

Edit `app.json` > `expo.extra.apiBaseUrl` to point to your Flask server's IP.

## User Roles

| Role | Login URL | Capabilities |
|------|-----------|-------------|
| **User** | `/` | Register, fill questionnaires, manage consent, export/delete data |
| **Organisation** | `/client` | Create questionnaires, view anonymised submissions |
| **Auditor** | `/admin/auditor-login` | Full audit trail, breach management, DSR tracking, compliance dashboard |

## GDPR Features

- **Article 5(1)(e)** - Data retention with configurable cleanup
- **Article 7** - Per-organisation consent withdrawal and reinstatement
- **Article 15** - Right to Access (view all stored data)
- **Article 17** - Right to Erasure (delete account or data only)
- **Article 20** - Right to Data Portability (CSV export)
- **Article 32** - Security (pgcrypto encryption, 2FA, CSRF, rate limiting, hash-chained audit trail)
- **Article 33** - Breach notification with 72-hour deadline tracking
- **Article 34** - Automated breach notification emails to affected users
- **Articles 12-23** - Data Subject Request tracking with 30-day deadlines
