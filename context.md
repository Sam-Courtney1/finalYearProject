# Project Context: GDPR-Compliant Organ Donation System

## Overview
A GDPR-compliant organ donation registration system with a Flask web app, React Native mobile app, and PostgreSQL database with field-level encryption. Three user types: **End Users** (fill questionnaires, exercise GDPR rights), **Clients/Organizations** (create questionnaires, view anonymized responses), and **External Auditors** (view full audit trail).

---

## Tech Stack
- **Backend**: Flask 3.0 (Python 3.11) with Jinja2 templates
- **Database**: PostgreSQL on AWS RDS (pgcrypto encryption)
- **Frontend**: Bootstrap 5.3.3 + custom CSS + Bootstrap Icons 1.11.3 + Inter font
- **Mobile**: React Native (Expo 54) with JWT auth
- **Hosting**: AWS Elastic Beanstalk (eu-west-1)
- **Email**: Gmail SMTP (App Password)
- **Testing**: pytest (10 test suites)

---

## Project Structure

```
finalYearProject/
├── application/
│   ├── routes/                     # 6 Flask blueprint files
│   │   ├── pages_and_actions.py    # auth_bp & pages_bp (login/register/GDPR rights)
│   │   ├── questionnaire_routes.py # questionnaire_bp (fill & edit questionnaires)
│   │   ├── home_route.py           # home_bp (user dashboard)
│   │   ├── client_routes.py        # client_bp (organization management)
│   │   ├── admin_routes.py         # admin_bp (audit/compliance dashboards)
│   │   └── api_routes.py           # api_bp (mobile JSON API with JWT)
│   ├── services/                   # 12 service modules
│   │   ├── authentication.py       # Password hashing & validation
│   │   ├── decorators.py           # @require_user_login, @require_client_login, @require_audit_access
│   │   ├── audit_service.py        # @audit_log decorator, SHA-256 hash chain
│   │   ├── otp_service.py          # 2FA OTP generation & verification
│   │   ├── email_service.py        # Gmail SMTP for OTP & password reset
│   │   ├── jwt_utils.py            # JWT token create/decode for mobile
│   │   ├── log_form_data.py        # Questionnaire submission handler
│   │   ├── dsr_service.py          # GDPR Data Subject Requests (30-day tracking)
│   │   ├── retention_service.py    # GDPR Article 5(1)(e) data retention cleanup
│   │   ├── breach_service.py       # GDPR Article 33 breach tracking (72h deadline)
│   │   ├── breach_notification_service.py  # Article 34 email notifications
│   │   └── compliance_service.py   # Overall compliance dashboard aggregator
│   └── extensions.py               # Flask-Limiter rate limiting
├── data/                           # 12 database modules
│   ├── db_connection.py            # PostgreSQL connection & context manager
│   ├── migrations.py               # Schema migrations on startup
│   ├── user_database.py            # User CRUD
│   ├── client_database.py          # Client/org CRUD
│   ├── questionnaire_client.py     # Client questionnaire field management
│   ├── questionnaire.py            # Legacy questionnaire insert
│   ├── submission_database.py      # Submission queries with encryption
│   ├── audit_database.py           # Audit log insertion & hash chain verification
│   ├── dsr_database.py             # Data Subject Request queries
│   ├── retention_database.py       # Inactive user & expired data queries
│   ├── breach_database.py          # Data breach CRUD
│   └── breach_notification_database.py  # Breach notification tracking
├── presentation/
│   ├── templates/                  # 30+ Jinja2 HTML templates
│   │   ├── base.html               # Master template (audit dashboard)
│   │   ├── base_auth.html          # Auth pages layout
│   │   ├── base_user.html          # Logged-in user layout
│   │   ├── base_client.html        # Client/org layout
│   │   ├── landing.html            # User login page
│   │   ├── Register.html           # User registration
│   │   ├── homepage.html           # User dashboard
│   │   ├── questionnaire.html      # Fill questionnaire
│   │   ├── questionnaire_select.html
│   │   ├── edit_select.html
│   │   ├── edit_answers.html
│   │   ├── access_data.html        # GDPR Right to Access
│   │   ├── consent_management.html # Consent withdrawal/reinstatement
│   │   ├── client_landing.html     # Org login
│   │   ├── client_register.html
│   │   ├── client_dashboard.html
│   │   ├── client_questionnaire_list.html
│   │   ├── client_create_questionnaire.html
│   │   ├── client_questionnaire.html
│   │   ├── client_view_submissions.html
│   │   ├── audit_dashboard.html    # Audit logs + Leaflet.js map
│   │   ├── dsr_dashboard.html      # DSR management
│   │   ├── breach_dashboard.html
│   │   ├── breach_detail.html
│   │   ├── retention_dashboard.html
│   │   ├── compliance_dashboard.html
│   │   ├── verify_2fa.html
│   │   ├── forgot_password.html
│   │   ├── reset_password.html
│   │   ├── privacy_policy.html
│   │   ├── auditor_login.html
│   │   └── error.html
│   └── static/
│       └── main.css                # Single CSS file with CSS custom properties
├── mobile_app/                     # React Native (Expo)
│   ├── app.json
│   ├── package.json
│   └── src/
│       ├── api/                    # 6 API client modules
│       │   ├── client.js           # Axios instance with JWT interceptor
│       │   ├── auth.js
│       │   ├── questionnaire.js
│       │   ├── submissions.js
│       │   ├── data.js
│       │   └── consent.js
│       ├── context/
│       │   └── AuthContext.js      # Global auth state + AsyncStorage
│       ├── screens/                # 10 React Native screens
│       │   ├── LoginScreen.js
│       │   ├── RegisterScreen.js
│       │   ├── HomeScreen.js
│       │   ├── QuestionnaireSelectScreen.js
│       │   ├── QuestionnaireScreen.js
│       │   ├── SubmissionsListScreen.js
│       │   ├── EditSubmissionScreen.js
│       │   ├── DataAccessScreen.js
│       │   ├── ConsentManagementScreen.js
│       │   └── SettingsScreen.js
│       ├── components/
│       │   ├── LoadingScreen.js
│       │   └── MenuCard.js
│       └── theme/
│           └── theme.js
├── tests/                          # 10 pytest test files
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_2fa.py
│   ├── test_access_control.py
│   ├── test_consent.py
│   ├── test_gdpr_rights.py
│   ├── test_password_reset.py
│   ├── test_client_routes.py
│   ├── test_audit.py
│   └── test_api.py
├── wsgi.py                         # Flask app factory & startup
├── client.py                       # Legacy separate client app (port 5001)
├── requirements.txt
├── .env                            # Environment variables
├── .ebextensions/
│   └── 01_flask.config             # EB deployment config
└── .elasticbeanstalk/
    └── config.yml                  # EB CLI config
```

---

## Blueprints & Endpoints

### auth_bp (no prefix) — `pages_and_actions.py`
| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/` | GET/POST | User login (landing page) | No |
| `/register` | GET | Registration page | No |
| `/register_user` | POST | Create user (rate-limited: 3/min) | No |
| `/login` | POST | Authenticate (rate-limited: 5/min) | No |
| `/verify_2fa` | GET/POST | 2FA OTP verification | Pending 2FA |
| `/forgot_password` | GET/POST | Password reset request | No |
| `/reset_password/<token>` | GET/POST | Reset with token | No |
| `/logout` | GET | Clear session | User |

### pages_bp (no prefix) — `pages_and_actions.py`
| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/access_data` | GET | GDPR Right to Access (Article 15) | User |
| `/delete_data` | POST | Right to Erasure (Article 17) | User |
| `/withdraw_consent/<id>` | POST | Revoke consent (Articles 7, 21) | User |
| `/reinstate_consent/<id>` | POST | Re-enable consent | User |

### questionnaire_bp (no prefix) — `questionnaire_routes.py`
| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/questionnaire` | GET | Select questionnaire | User |
| `/questionnaire/<client_id>/<name>` | GET/POST | Fill questionnaire | User |
| `/edit` | GET | Choose submission to edit | User |
| `/edit/<submission_id>` | GET/POST | Edit answers | User |

### home_bp (no prefix) — `home_route.py`
| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/homepage` | GET | User dashboard with stats | User |

### client_bp (`/client`) — `client_routes.py`
| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/client/` | GET/POST | Client login | No |
| `/client/register` | GET/POST | Client registration | No |
| `/client/logout` | GET | Client logout | Client |
| `/client/dashboard` | GET | Org dashboard | Client |
| `/client/questionnaires` | GET | List questionnaires | Client |
| `/client/questionnaire/create` | GET/POST | Create questionnaire | Client |
| `/client/questionnaire/<name>` | GET/POST | Edit fields | Client |
| `/client/delete_field/<id>` | POST | Remove field | Client |
| `/client/view_submissions/<name>` | GET | View anonymized submissions | Client |
| `/client/export/<name>` | GET | CSV export | Client |

### admin_bp (`/admin`) — `admin_routes.py`
| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/admin/` | GET | Audit dashboard (paginated, filterable) | Client or Auditor |
| `/admin/export` | GET | CSV export of audit logs | Client or Auditor |
| `/admin/auditor_login` | GET/POST | Auditor login | No |
| `/admin/auditor_register` | GET/POST | Auditor registration | No |
| `/admin/auditor_logout` | GET | Auditor logout | Auditor |
| `/admin/audit_chain_verification` | GET | Verify hash chain integrity | Client or Auditor |
| `/admin/breach` | GET/POST | Breach dashboard | Client or Auditor |
| `/admin/breach/<id>` | GET | Breach detail | Client or Auditor |
| `/admin/breach/<id>/notify` | POST | Send breach notification emails | Client or Auditor |
| `/admin/dsr` | GET | Data Subject Request dashboard | Client or Auditor |
| `/admin/dsr/<id>` | POST | Update DSR status | Client or Auditor |
| `/admin/retention` | GET | Retention dashboard | Client or Auditor |
| `/admin/retention/cleanup` | POST | Execute retention cleanup | Client or Auditor |
| `/admin/compliance` | GET | GDPR compliance overview | Client or Auditor |

### api_bp (`/api`) — `api_routes.py`
All return JSON. Require `Bearer <JWT>` token (except login/register).

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/register` | POST | Mobile registration |
| `/api/login` | POST | Login (returns JWT) |
| `/api/logout` | POST | Log logout event |
| `/api/user/data` | GET | Right to Access (grouped by company) |
| `/api/user/data/export` | GET | Export to JSON |
| `/api/user/delete` | POST | Right to Erasure |
| `/api/questionnaires` | GET | Available questionnaires |
| `/api/questionnaire/<client_id>/<name>` | GET/POST | Fill questionnaire |
| `/api/submissions` | GET | User's submissions |
| `/api/submission/<id>` | PUT | Update submission |
| `/api/submission/<id>` | DELETE | Delete submission |
| `/api/consent/<id>/withdraw` | POST | Withdraw consent |
| `/api/consent/<id>/reinstate` | POST | Reinstate consent |

---

## Database Schema

**PostgreSQL on AWS RDS** with `pgcrypto` extension.

| Table | Purpose |
|-------|---------|
| `users` | End users (username, password_hash, email_enc, last_login) |
| `clients` | Organizations (username, password_hash) |
| `questionnaire_fields` | Dynamic field definitions (field_label, field_type, category, questionnaire_name) |
| `submissions` | Questionnaire responses (user_id, client_id, consent, consent_withdrawn, questionnaire_name, deleted) |
| `answers` | Encrypted field responses (submission_id, field_id, value, updated_at) |
| `pii` | PII data (first_name_enc, address_enc) |
| `demographic_data` | Age and demographics |
| `audit_logs` | Tamper-evident trail (SHA-256 hash chain linking) |
| `otp_tokens` | 2FA codes (token_hash, expires_at, attempts) |
| `password_reset_tokens` | Reset tokens (token_hash, expires_at, used) |
| `data_subject_requests` | GDPR DSRs (request_type, status, deadline — 30 days) |
| `data_breaches` | Security incidents (severity, discovered_at, reported_at, affected_users_count) |
| `breach_notifications` | Breach email tracking (status: pending/sent/failed) |
| `auditors` | External auditors (username, password_hash) |

### Encryption Strategy
- **PII/Medical fields**: `pgp_sym_encrypt(data, APP_ENC_KEY)` → stored as BYTEA
- **Decryption**: `pgp_sym_decrypt(value::bytea, APP_ENC_KEY)` on read
- **Passwords**: `werkzeug.security.generate_password_hash()` (one-way)
- **Hashed fields**: One-way hash, cannot be edited

---

## Services

| Service | Purpose |
|---------|---------|
| `authentication.py` | Password validation (8+ chars, upper/lower/digit/special), hashing, verification |
| `decorators.py` | Route protection: `@require_user_login`, `@require_client_login`, `@require_audit_access` |
| `audit_service.py` | `@audit_log` decorator, SHA-256 hash chain, logs who/what/when/where |
| `otp_service.py` | 6-digit OTP (10-min expiry, 3-attempt limit), password reset tokens (1-hour expiry) |
| `email_service.py` | Gmail SMTP: OTP emails, password reset links |
| `jwt_utils.py` | HS256 JWT tokens (24-hour expiry) for mobile app |
| `log_form_data.py` | Questionnaire submission: encrypts PII/Medical, hashes Hashed fields |
| `dsr_service.py` | GDPR DSR logging with 30-day deadline (Article 12(3)) |
| `retention_service.py` | Article 5(1)(e): identifies inactive users & expired submissions, dry-run or soft-delete |
| `breach_service.py` | Article 33: 72-hour deadline tracking, breach severity, status management |
| `breach_notification_service.py` | Article 34: batch email notifications to affected users |
| `compliance_service.py` | Aggregates breach/DSR/retention metrics, returns overall compliance status |

---

## Security Features

- **Encryption**: pgp_sym_encrypt for PII/Medical fields at rest
- **CSRF**: All POST forms require `{{ csrf_token() }}`
- **Rate Limiting**: 3 register/min, 5 login/min, 200/day global
- **Session Security**: HTTPOnly cookies, 10-minute timeout, Lax SameSite
- **2FA**: 6-digit OTP via email (10-min expiry, 3-attempt limit)
- **Password Policy**: 8+ chars, upper + lower + digit + special character
- **Audit Trail**: SHA-256 hash chain linking (tamper-evident)
- **Age Validation**: 16-120 years

---

## GDPR Compliance

| Article | Implementation |
|---------|---------------|
| **5(1)(a)** Lawfulness | Explicit consent before questionnaire submission |
| **5(1)(e)** Storage Limitation | `retention_service.py` — identifies & deletes expired data |
| **7** Consent Withdrawal | `/withdraw_consent/<id>`, `/api/consent/<id>/withdraw` |
| **12** Response Deadlines | 30-day tracking in `data_subject_requests` table |
| **15** Right to Access | `/access_data`, `/api/user/data` — decrypted data export |
| **17** Right to Erasure | `/delete_data`, `/api/user/delete` — cascading soft-delete |
| **21** Right to Object | Mapped to consent withdrawal |
| **32** Security | Encryption, hashing, CSRF, rate limiting, session timeout, audit trail |
| **33** Breach Reporting | 72-hour deadline tracking, severity levels, status management |
| **34** Breach Notification | Batch email to affected users with GDPR Article 34 footer |

---

## Template Inheritance

```
base.html
├── base_auth.html → forgot_password, reset_password, verify_2fa
├── base_user.html → homepage, questionnaire, edit, access_data, consent_management
├── base_client.html → client_landing, client_dashboard, client_questionnaire_*, client_view_submissions
├── landing.html, Register.html (extend base.html directly)
├── audit_dashboard, dsr_dashboard, breach_*, retention_dashboard, compliance_dashboard
├── auditor_login, privacy_policy, error
```

### CSS (`main.css`)
- CSS custom properties: `--color-primary: #7c3aed` (purple), semantic colors, spacing, shadows
- Animations: fadeInUp, fadeIn, slideIn, scaleIn
- Accessibility: skip-to-content, large text toggle, high contrast mode, OpenDyslexic font option
- Session timeout warning: JavaScript timer at 9min, redirect at 10min

---

## Mobile App Architecture

- **Navigation**: React Navigation (stack-based)
- **HTTP Client**: Axios with JWT bearer token interceptor
- **Auth State**: React Context + AsyncStorage persistence
- **Base URL**: Configurable in `api/client.js`
- **Screens**: Login, Register, Home, QuestionnaireSelect, Questionnaire, SubmissionsList, EditSubmission, DataAccess, ConsentManagement, Settings

---

## Deployment

- **Platform**: AWS Elastic Beanstalk (Python 3.11, Amazon Linux 2023)
- **Region**: eu-west-1
- **Database**: AWS RDS PostgreSQL (7-day automatic snapshots)
- **WSGI**: gunicorn
- **Health Check**: `/health` → `{"status": "healthy"}`
- **Config**: `.ebextensions/01_flask.config`

---

## Environment Variables (.env)

| Variable | Purpose |
|----------|---------|
| `DB_HOST` | RDS PostgreSQL hostname |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `APP_ENC_KEY` | pgp_sym_encrypt/decrypt key |
| `CLIENT_APP_SECRET_KEY` | Flask session secret (legacy) |
| `SES_SENDER_EMAIL` | Sender email address |
| `AWS_REGION` | AWS region |
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `SMTP_EMAIL` | Gmail address |
| `SMTP_PASSWORD` | Gmail App Password |

---

## Testing

10 pytest test files with fixtures in `conftest.py`:
- `app` — Flask test app with DB mocking
- `client` — Unauthenticated test client
- `auth_client` — Logged-in user
- `client_auth_client` — Logged-in org
- `auditor_client` — Logged-in auditor

Tests cover: auth, 2FA, access control, consent, GDPR rights, password reset, client routes, audit chain, mobile API.
