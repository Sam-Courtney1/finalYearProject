# Organ Donation System — GDPR-Compliant Data Platform

A Flask web application and companion React Native mobile app that lets data subjects
exercise their GDPR rights (access, rectification, erasure, portability, consent
withdrawal) over an encrypted organ-donor questionnaire database. External auditors
and organisations ("clients") can monitor activity through a tamper-evident audit
log backed by a SHA-256 hash chain.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Flask 3, Python 3.11, Gunicorn |
| Database | PostgreSQL + `pgcrypto` (AES-256 encryption at rest) |
| Web frontend | Jinja2 templates, Bootstrap 5.3, custom CSS, Leaflet.js (audit map) |
| Mobile app | React Native via Expo 54 (WebView wrapper) |
| Hosting | AWS Elastic Beanstalk (Amazon Linux 2023) + AWS RDS (PostgreSQL) |
| Build tool (mobile) | EAS Build |

---

## Project structure

```
finalYearProject/
├── application/
│   ├── routes/              # Flask blueprints (6 files)
│   │   ├── admin_routes.py      # /admin  - auditor + client audit dashboard
│   │   ├── api_routes.py        # /api    - mobile JSON endpoints (JWT auth)
│   │   ├── client_routes.py     # /client - organisation management
│   │   ├── home_route.py        # /homepage
│   │   ├── pages_and_actions.py # /, /login, /register, GDPR rights
│   │   └── questionnaire_routes.py
│   ├── services/            # Business logic (auth, audit, DSR, breach, etc.)
│   └── extensions.py        # flask-limiter instance
├── data/                    # Database layer (psycopg2)
├── presentation/
│   ├── templates/           # Jinja2 templates (18 files)
│   └── static/              # main.css, tutorial.js
├── mobile_app/              # Expo / React Native wrapper
├── tests/                   # pytest test suite
├── seed_database.sql        # Full DB reset + sample data
├── wsgi.py                  # Flask entrypoint (create_app factory)
├── requirements.txt
├── pytest.ini
└── Procfile                 # gunicorn command for Elastic Beanstalk
```

---

## Environment variables

Create a `.env` file in the project root (gitignored). All required in production:

| Variable | Purpose |
| --- | --- |
| `FLASK_SECRET_KEY` | Flask session cookie signing key. |
| `APP_ENC_KEY` | pgcrypto symmetric key for encrypting PII / Medical / email columns. **Do not rotate without re-encrypting existing rows.** |
| `JWT_SECRET_KEY` | HS256 signing key for mobile JWT tokens. |
| `DB_HOST` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL connection details. |
| `SMTP_EMAIL` / `SMTP_PASSWORD` | Gmail SMTP credentials for 2FA OTP + breach notifications. |
| `APP_BASE_URL` | Public base URL, used in password reset emails. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of origins allowed to call `/api/*`. |
| `LOG_LEVEL` | `INFO` / `DEBUG` / `WARNING` (default INFO). |

Each of `FLASK_SECRET_KEY`, `APP_ENC_KEY`, `JWT_SECRET_KEY` is rejected if set to the literal string `"test"` in production — see `wsgi.py` and `jwt_utils.py`.

---

## Local development

```powershell
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Create .env with the variables listed above

# 3. Enable pgcrypto on your database (one-off)
psql -d your_db -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# 4. Seed the database (see section below)

# 5. Run
python wsgi.py
# Default: http://0.0.0.0:5000
```

Tests:

```powershell
pytest
```

---

## Database seeding

`seed_database.sql` wipes and re-populates the database with sample auditors,
clients, users, questionnaires, submissions, DSRs, and a test breach. It also
truncates `audit_logs` so the hash chain resets to a valid `GENESIS` state.

Run in DBeaver (open the file → select all → Alt+X) or via psql:

```powershell
psql "host=your-db-host dbname=your-db user=your-user" -f seed_database.sql
```

**Important:** The file assumes `APP_ENC_KEY=sam`. If you use a different key, find-and-replace
`'sam'` in the `pgp_sym_encrypt(..., 'sam', ...)` calls before running.

### Seeded login credentials

Every seeded account uses the password `Password123!`.

| Role | Username | Login path |
| --- | --- | --- |
| Auditor | `auditor1` | `/admin/auditor-login` |
| Client (organisation) | `HospitalA` / `ResearchOrg` / `DonorNetwork` | `/client` |
| End user | `alice` / `bob` / `carol` / `dave` / `eve` | `/` |

Note: `dave`'s submission to `DonorNetwork` has consent withdrawn on purpose, so
DonorNetwork's "View Submissions" page will correctly appear empty. Use HospitalA
or ResearchOrg to see populated data.

---

## Deployment — AWS Elastic Beanstalk

```powershell
# First time: initialise EB on this directory
eb init

# Set production environment variables (one line)
eb setenv FLASK_SECRET_KEY=xxx APP_ENC_KEY=xxx JWT_SECRET_KEY=xxx `
         DB_HOST=xxx DB_NAME=xxx DB_USER=xxx DB_PASSWORD=xxx `
         SMTP_EMAIL=xxx SMTP_PASSWORD=xxx APP_BASE_URL=https://your-domain

# Deploy latest commit
eb deploy

# Inspect live status and logs
eb status
eb health
eb logs --all
```

`Procfile` tells EB to start the app with gunicorn. The health check hits `/health`,
defined in `wsgi.py`.

---

## Mobile app

The mobile app is a thin WebView wrapper around the deployed website, so **web-only
changes do not require a mobile rebuild** — the next launch of the existing APK will
pick up the new CSS / JS / templates automatically.

```powershell
cd mobile_app
npm install          # once
npm run build:android  # runs: eas build --platform android --profile preview
```

Change `app.json` → `extra.websiteUrl` to point at the EB CNAME or a custom domain.

---

## Key features

### GDPR rights (end user)
- **Right to access** — decrypts and displays all stored PII/Medical fields
- **Right to rectification** — edit previously submitted answers; re-encrypted transparently
- **Right to erasure** — full account deletion (with audit log anonymisation)
  or per-submission deletion
- **Right to data portability** — CSV export
- **Consent management** — per-submission withdrawal and reinstatement

### Client (organisation) features
- Create / edit questionnaires with custom fields categorised as PII, Medical,
  Demographic, or Hashed
- View anonymised respondent data ("Respondent 1", "Respondent 2" …) with PII
  decrypted on demand; rows with withdrawn consent are hidden

### Auditor / admin features
- Full audit log dashboard with action / actor / date filtering
- SHA-256 hash-chain integrity verification (tamper evidence)
- Leaflet IP geolocation map
- Breach register with 72-hour GDPR reporting countdown and user email notifications
- DSR dashboard with 30-day deadline tracking
- Data retention dashboard (inactive users, expired submissions) with dry-run preview
- Compliance overview rolling up breach / DSR / retention / backup status
- CSV export of audit logs (formula-injection sanitised)

### Security
- **Encryption at rest** — pgcrypto `pgp_sym_encrypt` (AES-256) on PII, Medical,
  and email columns
- **Password hashing** — werkzeug scrypt
- **2FA** — email-delivered 6-digit OTP on every login (SMTP)
- **JWT** — mobile API auth, in-memory revocation list
- **CSRF** — Flask-WTF on all browser POST forms (mobile API exempted)
- **Rate limiting** — Flask-Limiter on `/login`, `/register`, `/forgot-password`, etc.
- **Audit log chain** — every entry carries `previous_hash`; `verify_audit_chain()`
  detects any edit / delete
- **Headers** — CSP, HSTS (prod), X-Frame-Options, X-Content-Type-Options
- **Retention** — 365-day default with anonymisation after 7 years for audit logs

---

## Health checks

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Returns `{"status": "healthy"}`. Used by the Elastic Beanstalk ELB. Exempt from rate limiting. |
| `GET /ping` | Lightweight keep-alive hit by the "Stay Logged In" button in the user navbar. |
