# Organ Donation System - File Explanations

A complete breakdown of every Python, HTML and static file in the project, explaining what each file does and how it fits into the system.

---

## Python Files

### `wsgi.py` - Application Entry Point

This is the main file that starts the entire Flask application. It:

- Creates the Flask app instance using a `create_app()` factory function
- Loads environment variables from a `.env` file
- Configures Flask to find HTML templates in `presentation/templates/` and static files (CSS/JS) in `presentation/static/`
- Sets the secret key for session management from an environment variable
- Enables CORS for the `/api/*` routes so the React Native mobile app can make cross-origin requests
- Imports and registers all 7 Flask Blueprints (`auth_bp`, `pages_bp`, `questionnaire_bp`, `home_bp`, `client_bp`, `admin_bp`, `api_bp`)
- Initialises the audit logging table and runs database migrations on startup
- When run directly, starts the Flask development server on port 5000

### `client.py` - Legacy Client App (Standalone)

This is an older, standalone Flask app for clients (organisations) that runs on port 5001. It was the original client portal before client routes were moved into the main app via `client_routes.py`. It contains:

- Client login, registration, and logout
- A client dashboard
- Questionnaire field management (add/delete fields)
- It uses its own Flask instance rather than a Blueprint

This file is largely superseded by `client_routes.py` but still exists in the codebase.

---

### `data/` - Database Layer

#### `data/db_connection.py` - Database Connection

Establishes a connection to the PostgreSQL database using `psycopg2`. Connection credentials (host, database name, user, password) are loaded from environment variables to avoid hardcoding secrets. Returns a connection object or `None` if the connection fails.

#### `data/user_database.py` - User Database Operations

Handles all database operations related to end users:

- `find_by_username(username)` - Looks up a user by username, returns their ID and hashed password (used for login)
- `insert_user(username, hashed_password)` - Inserts a new user into the `users` table
- `get_user_data(user_id)` - Retrieves ALL data stored about a user for the "Right to Access" page. Joins across `users`, `submissions`, `pii`, `demographic_data`, `answers`, `questionnaire_fields`, and `clients` tables. Decrypts encrypted PII and Medical fields using `pgp_sym_decrypt`. Returns both "static data" (name, address, age from registration) and "dynamic data" (per-organisation questionnaire answers)
- `delete_user(user_id)` - Deletes a user and all their data (cascading) for "Right to Forget"
- `get_user_data_for_client(client_id)` - Returns questionnaire data for a specific client, but only where consent has NOT been withdrawn
- `delete_user_data_only(user_id)` - Deletes all submissions/answers but keeps the user account intact

#### `data/client_database.py` - Client Database Operations

Handles database operations for client (organisation) accounts:

- `insert_client(username, password_hash)` - Inserts a new client into the `clients` table, returns the new `client_id`
- `find_client_by_username(username)` - Looks up a client by username, returns `client_id`, `username`, and `password_hash` (used for login authentication)

#### `data/questionnaire.py` - Questionnaire Data Insertion (Legacy)

Handles inserting a completed questionnaire into the database. It:

- Creates a `submissions` record linking the user to their consent choice
- Inserts encrypted PII fields (name, address) into the `pii` table using `pgp_sym_encrypt`
- Inserts encrypted medical data (blood type, organ) into the `medical_data` table using `pgp_sym_encrypt`
- Inserts demographic data (age) into the `demographic_data` table as plain text

This file handles the older "static" questionnaire fields. The newer dynamic questionnaire submissions are handled by `log_form_data.py`.

#### `data/questionnaire_client.py` - Client Questionnaire Field Management

Handles the CRUD operations for questionnaire fields that clients create:

- `insert_field(client_id, questionnaire_name, label, field_type, category, is_required)` - Adds a new field to a specific questionnaire. Fields have a label, type (text/number), and category (PII, Medical, Demographic, or Hashed) which determines how the data is stored
- `get_fields_for_client(client_id, questionnaire_name)` - Returns all fields for a specific questionnaire, used to display the field editor
- `delete_field(field_id, client_id)` - Removes a field from a questionnaire
- `get_questionnaires_for_client(client_id)` - Returns all distinct questionnaire names for a client with field counts and active submission counts
- `questionnaire_name_exists(client_id, questionnaire_name)` - Checks if a questionnaire name already exists for duplicate prevention

#### `data/submission_database.py` - Submission & Consent Management

Handles retrieving, editing, and managing consent for questionnaire submissions:

- `get_user_submissions(user_id)` - Returns all of a user's questionnaire submissions (excluding deleted ones and the registration submission), with client name and questionnaire name. Used by both the edit page and consent management page
- `get_submission_answers(submission_id, user_id)` - Decrypts and returns all answers for a specific submission. Verifies ownership and excludes Hashed fields (which can't be displayed)
- `update_submission_answers(submission_id, user_id, updated_fields)` - Updates answers with appropriate re-encryption. PII/Medical fields are re-encrypted, Hashed fields are skipped, plain text is stored as-is. Only updates values that actually changed
- `get_submissions_for_questionnaire(client_id, questionnaire_name)` - Returns anonymised submission data for clients to view. User identities are replaced with "Respondent 1", "Respondent 2", etc. Respects consent withdrawal and soft-deletion
- `withdraw_consent(submission_id, user_id)` - Sets the `consent_withdrawn` flag to TRUE
- `reinstate_consent(submission_id, user_id)` - Clears the `consent_withdrawn` flag
- `delete_single_submission(submission_id, user_id)` - Hard deletes answers and soft deletes the submission record (keeps it for audit trail)

#### `data/audit_database.py` - Audit Log Database Operations

Implements a tamper-evident audit logging system for GDPR Article 32 compliance:

- `create_audit_table()` - Creates the `audit_logs` table with indexes if it doesn't exist. Called on app startup
- `get_last_hash()` - Retrieves the SHA-256 hash of the most recent log entry for chain linking
- `compute_hash(...)` - Computes a SHA-256 hash of a log entry's data for tamper detection
- `insert_audit_log(...)` - Inserts a new log entry with hash chain linking. Each entry stores the previous entry's hash, making it detectable if logs are modified or deleted
- `get_audit_logs(...)` - Retrieves logs with optional filtering by actor, action, date range, with pagination
- `get_audit_log_count(...)` - Gets total count of matching logs for pagination calculations
- `verify_audit_chain()` - Walks through every log entry and verifies: (1) each entry's `previous_hash` matches the prior entry's `current_hash`, and (2) each entry's stored hash matches a freshly computed hash. Returns `True` if chain is intact, `False` if tampered
- `get_user_audit_logs(user_id)` - Gets logs for a specific user
- `get_logs_for_record(target_table, target_id)` - Gets all logs related to a specific database record
- `get_action_summary(...)` - Counts actions by type for the dashboard statistics

#### `data/migrations.py` - Database Schema Migrations

Runs schema migrations on application startup to keep the database up to date. Uses `IF NOT EXISTS` and `ADD COLUMN IF NOT EXISTS` so migrations are safe to run multiple times. Migrations include:

- Adding `consent_withdrawn` and `consent_withdrawn_at` columns to `submissions`
- Adding `updated_at` timestamp to `answers` for tracking edits
- Adding `deleted`, `deleted_at`, and `deletion_reason` columns to `submissions` for soft deletion
- Adding `questionnaire_name` column to `questionnaire_fields` and `submissions` for supporting multiple questionnaires per client
- Creating appropriate indexes for efficient queries

---

### `application/services/` - Business Logic Layer

#### `application/services/authentication.py` - User Authentication

Two simple functions:

- `register_user(username, password)` - Hashes the password using Werkzeug's `generate_password_hash` (PBKDF2) and inserts the user into the database
- `authenticate_user(username, password)` - Looks up the user by username, checks the password against the stored hash using `check_password_hash`. Returns the `user_id` if valid, `None` otherwise

#### `application/services/jwt_utils.py` - JWT Token Utilities

Handles JWT (JSON Web Token) creation and validation for the mobile API:

- `create_token(user_id, username)` - Creates a signed JWT token containing the user's ID and username, set to expire in 24 hours. Uses the same encryption key as the rest of the app
- `decode_token(token)` - Validates and decodes a JWT token. Returns the payload if valid, `None` if expired or invalid

#### `application/services/audit_service.py` - Audit Logging Service

Provides the `@audit_log` decorator and helper functions for logging all actions:

- `get_client_ip()` - Gets the real client IP, handling proxies and load balancers
- `get_actor_info()` - Determines who is performing the action from the session (user, client, or anonymous)
- `@audit_log(action, target_table)` - A decorator that automatically logs route access. Captures who, what, when, where (IP, user agent), and what data was accessed
- `log_login_success()` / `log_login_failed()` / `log_logout()` - Log authentication events
- `log_data_access()` / `log_data_create()` / `log_data_update()` / `log_data_delete()` - Log CRUD operations on data
- `log_data_export()` - Logs when a user exports their data

#### `application/services/log_form_data.py` - Questionnaire Submission Handler

Handles the submission of dynamic (client-created) questionnaire forms:

- `handle_questionnaire_submission(user_id, client_id, questionnaire_name, form_data)` - Creates a `submissions` record, then loops through all form fields starting with `field_`. For each field, it checks the category and applies the appropriate security:
  - **PII / Medical** fields are encrypted using `pgp_sym_encrypt` before storage
  - **Hashed** fields are one-way hashed using `generate_password_hash` (cannot be recovered)
  - **Demographic** fields are stored as plain text

---

### `application/routes/` - Route Handlers (Controllers)

#### `application/routes/home_route.py` - Homepage Route

Contains a single route:

- `GET /homepage` - Displays the user homepage if they're logged in (checks for `username` in session). If not logged in, redirects to the login page

#### `application/routes/pages_and_actions.py` - Auth & GDPR Rights Routes

Contains two Blueprints: `auth_bp` for authentication and `pages_bp` for GDPR rights pages.

**auth_bp routes:**
- `GET /` - Displays the landing page with login form
- `GET /register` - Displays the registration form
- `POST /register_user` - Processes registration: validates unique username, hashes password, creates user, inserts encrypted PII (name, address) and demographic data (age) into the database, logs the event
- `POST /login` - Authenticates user credentials, sets session, logs the event
- `GET /logout` - Clears session, logs the event

**pages_bp routes:**
- `GET /right_to_access` - Shows all stored data about the user (GDPR Article 15). Decrypts and displays both core info and per-organisation questionnaire answers
- `POST /right_to_forget` - Deletes the user account and all associated data (GDPR Article 17)
- `POST /delete_user_data` - Deletes all questionnaire data but keeps the account
- `GET /consent` - Shows consent management page with per-submission consent status
- `POST /consent/withdraw/<submission_id>` - Withdraws consent for a specific submission
- `POST /consent/reinstate/<submission_id>` - Re-gives consent for a previously withdrawn submission
- `POST /delete_submission/<submission_id>` - Permanently deletes a single submission
- `GET /privacy` - Displays the privacy policy page
- `GET /export_data` - Exports all user data as a CSV file (GDPR Article 20 - Right to Data Portability)

#### `application/routes/questionnaire_routes.py` - Questionnaire Routes

Handles filling out and editing questionnaires:

- `GET /questionnaire` - Shows a two-step selection: first pick an organisation, then pick a specific questionnaire from that organisation
- `GET/POST /questionnaire/<client_id>/<questionnaire_name>` - Displays the questionnaire form (GET) or processes the submission (POST). Shows all client-defined fields and a consent checkbox
- `GET /edit` - Shows a list of the user's previous submissions they can edit, with delete buttons
- `GET /edit/<submission_id>` - Shows a pre-populated form with current decrypted answers for editing
- `POST /edit/<submission_id>` - Saves edited answers with re-encryption where needed

#### `application/routes/client_routes.py` - Client (Organisation) Routes

All routes are prefixed with `/client`. Handles the client-side portal:

- `GET/POST /client/` - Client login page (landing page with login form)
- `GET/POST /client/register` - Client registration
- `GET /client/logout` - Client logout
- `GET /client/dashboard` - Client dashboard with links to manage questionnaires, view submissions, and audit logs
- `GET /client/questionnaires` - Lists all of the client's questionnaires with field counts and submission counts
- `GET/POST /client/questionnaire/create` - Create a new questionnaire (enter a name)
- `GET/POST /client/questionnaire/<questionnaire_name>` - Edit a specific questionnaire's fields (add new fields, view existing ones)
- `POST /client/delete_field/<field_id>` - Delete a field from a questionnaire
- `GET /client/questionnaire/<questionnaire_name>/data` - View anonymised submission data for a questionnaire. Respondents are shown as "Respondent 1", "Respondent 2", etc.

#### `application/routes/admin_routes.py` - Audit Dashboard Routes

All routes are prefixed with `/admin`. Provides the audit log dashboard for GDPR compliance monitoring:

- `GET /admin/` - Main audit dashboard. Shows statistics (total logs, logins, failed logins, data access events), hash chain integrity status, filterable/paginated audit log table, and an interactive Leaflet.js map for geolocating IP addresses
- `GET /admin/export` - Exports filtered audit logs as a CSV file
- `GET /admin/verify-chain` - Re-verifies the integrity of the audit log hash chain
- `GET /admin/init` - Initialises the audit table (first-time setup)
- `GET /admin/geolocate/<ip>` - Returns geolocation data for an IP address using ip-api.com (used by the map)

Access is restricted to logged-in clients via the `require_client_login` decorator.

#### `application/routes/api_routes.py` - Mobile API Routes

All routes are prefixed with `/api`. Returns JSON for the React Native mobile app. Uses JWT tokens instead of session cookies.

**Auth:**
- `POST /api/register` - Register a new user, returns a JWT token
- `POST /api/login` - Login, returns a JWT token
- `POST /api/logout` - Logs the logout event

**GDPR Rights:**
- `GET /api/user/data` - Returns all stored data as JSON (Right to Access)
- `DELETE /api/user/account` - Deletes the user account and all data (Right to Forget)
- `DELETE /api/user/data` - Deletes questionnaire data but keeps account

**Questionnaires:**
- `GET /api/clients` - Lists all organisations with their questionnaires
- `GET /api/questionnaire/<client_id>/<questionnaire_name>` - Returns questionnaire fields for form building
- `POST /api/questionnaire/<client_id>/<questionnaire_name>` - Submits questionnaire answers

**Edit Answers:**
- `GET /api/submissions` - Lists user's submissions
- `GET /api/submissions/<id>/answers` - Returns decrypted answers for a submission
- `PUT /api/submissions/<id>/answers` - Updates answers

**Consent Management:**
- `GET /api/consent` - Lists consent status for all submissions
- `POST /api/submissions/<id>/consent/withdraw` - Withdraws consent
- `POST /api/submissions/<id>/consent/reinstate` - Re-gives consent
- `DELETE /api/submissions/<id>` - Deletes a single submission

The `@token_required` decorator validates the JWT token from the `Authorization: Bearer <token>` header and puts user info into the session so audit logging still works.

---

## HTML Templates

### Base Templates (Template Inheritance)

#### `base.html` - Root Base Template

The foundation template that all other templates extend. Contains:

- HTML document structure with `<head>` (meta tags, Google Fonts for Inter, Bootstrap 5.3.3 CSS, Bootstrap Icons 1.11.3, and the custom `main.css`)
- Block placeholders for `title`, `body_class`, `navbar`, `flash_messages`, `content`, and `extra_scripts`
- A cookie/privacy notice banner that uses `localStorage` to remember when dismissed
- Bootstrap 5 JS bundle at the bottom

#### `base_auth.html` - Authentication Pages Base

Extends `base.html`. Used by login and registration pages. Provides:

- A centred auth card layout with a background
- Blocks for `auth_title`, `auth_back` (back arrow), `card_title`, and `card_content`
- Flash message display within the card

#### `base_user.html` - Logged-In User Pages Base

Extends `base.html`. Provides a navigation bar for authenticated users with links to:

- Home (homepage)
- Questionnaire (fill a questionnaire)
- Consent (manage consent)
- Logout

The navbar highlights the currently active page.

#### `base_client.html` - Client/Organisation Pages Base

Extends `base.html`. Provides a navigation bar for authenticated clients with links to:

- Dashboard
- Questionnaires (manage)
- Audit Logs
- Logout

### User-Facing Pages

#### `landing.html` - User Landing/Login Page

Extends `base.html` directly (not `base_auth.html`). This is the main entry point of the application. Features:

- An animated background with a grid of fake donor data records
- A "spotlight" effect where moving your cursor reveals the encrypted version of the data
- Canvas-based animated grid lines and cursor echo trails
- A hero section with the headline "Your Data. Encrypted. Protected. Yours."
- A login card with username/password fields and a register link
- Feature badges showing AES-256, pgcrypto, Audit Trail, and Right to Forget
- Loads `landing.js` for the interactive effects

#### `login.html` - Simple Login Page

Extends `base_auth.html`. A simpler login form without the animated background. Contains username and password fields and a link to register. This is an alternative to the landing page login.

#### `Register.html` - User Registration Page

Extends `base_auth.html`. Registration form with:

- Username, password, age, and address fields
- A privacy consent checkbox that links to the privacy policy
- A back arrow to return to the login page

#### `homepage.html` - User Dashboard

Extends `base_user.html`. The main dashboard after login showing a greeting and four action cards:

- **Right to Access** - View all stored personal data
- **Edit Answers** - Modify questionnaire responses
- **Manage Consent** - Control how data is used
- **Delete Account** - Exercise right to be forgotten (with confirmation dialog)

#### `questionnaire_select.html` - Questionnaire Selection

Extends `base_user.html`. A two-step selection process:

1. **Step 1**: Lists all organisations that have questionnaires. Clicking one reveals step 2
2. **Step 2**: Lists the specific questionnaires available from the selected organisation

Uses JavaScript to show/hide the steps with a back button.

#### `questionnaire.html` - Fill a Questionnaire

Extends `base_user.html`. Displays a form with:

- The organisation name and questionnaire name as headers
- All dynamic fields defined by the client (label, input type based on field_type)
- A consent checkbox with a detailed consent statement
- A link to the privacy policy
- A submit button

#### `access_data.html` - Right to Access Page

Extends `base_user.html`. Displays all data stored about the user (GDPR Article 15):

- **Core Information** table showing first name, address, and age
- **Per Company Data** sections, each showing the organisation name, consent status (Active/Withdrawn badge), an edit button, and a table of field labels, categories, and values
- An "Export CSV" button to download all data

#### `edit_select.html` - Select Submission to Edit

Extends `base_user.html`. Lists all of the user's questionnaire submissions as cards, each showing:

- Organisation name and questionnaire name
- Consent status badge
- An Edit button to modify answers
- A Delete button with confirmation dialog

#### `edit_answers.html` - Edit Questionnaire Answers

Extends `base_user.html`. A pre-populated form showing current decrypted values for each field:

- Labels show which fields are encrypted (PII/Medical get a lock badge)
- An info note about one-way encrypted (Hashed) fields not being editable
- Save Changes and Cancel buttons

#### `consent_management.html` - Manage Consent

Extends `base_user.html`. A table showing all submissions with:

- Organisation name and questionnaire name
- Consent status (Active/Withdrawn badge)
- Withdraw or Re-give consent button
- Delete button for permanent deletion
- An info banner explaining GDPR Article 7(3) rights

#### `privacy_policy.html` - Privacy Policy

Extends `base.html` directly. A comprehensive GDPR privacy policy page with 9 sections:

1. **Data Controller** - TU Dublin academic project
2. **What Data We Collect** - Table showing PII, Medical, Demographic, and Authentication data with their protection methods
3. **Why We Collect Your Data** - Legal basis (explicit consent, Article 6(1)(a))
4. **Who Can See Your Data** - Users see their own, clients see anonymised only
5. **How Long We Keep Your Data** - Retention and deletion policies
6. **Your Rights Under GDPR** - Six rights cards (Access, Rectification, Erasure, Portability, Withdraw Consent, Restrict Processing)
7. **How We Protect Your Data** - AES-256 encryption, PBKDF2 hashing, hash chain audit trail
8. **Cookies** - Only a strictly necessary session cookie
9. **Contact & Complaints** - DPC Ireland

### Client-Facing Pages

#### `client_landing.html` - Client Portal Landing Page

Extends `base.html` directly. A visually rich landing page for the client portal with:

- An animated particle network background (canvas-based)
- Ambient glow orbs and a background grid
- Glass-style badges (GDPR Compliant, Real-time Audit, End-to-End Encrypted)
- A gradient headline "Compliance Made Effortless"
- A login card for client sign-in
- A trust bar with feature highlights
- Navigation links to Privacy Policy, Portal, and Get Started (register)
- Loads `client_landing.js` for the particle animation

#### `client_login.html` - Simple Client Login

Extends `base_auth.html`. A simpler client login form (alternative to the landing page). Has organisation name and password fields, plus a register link.

#### `client_register.html` - Client Registration

Extends `base_auth.html`. Registration form for new client organisations with company name and password fields, plus a back arrow to the login page.

#### `client_dashboard.html` - Client Dashboard

Extends `base_client.html`. The main client dashboard with three action cards:

- **Manage Questionnaires** - Create, edit, and manage questionnaire fields
- **View Submissions** - Browse anonymised respondent data
- **Audit Logs** - Monitor activity and verify data integrity

#### `client_questionnaire_list.html` - Questionnaire List

Extends `base_client.html`. Shows a table of all the client's questionnaires with:

- Questionnaire name
- Number of fields
- Number of active submissions
- Action buttons: Edit Fields and View Data
- A "Create New Questionnaire" button at the top
- Empty state message if no questionnaires exist

#### `client_create_questionnaire.html` - Create New Questionnaire

Extends `base_client.html`. A simple form to create a new questionnaire by entering a name. Validates that the name isn't already taken. On success, redirects to the field editor.

#### `client_questionnaire.html` - Questionnaire Field Editor

Extends `base_client.html`. The editor for a specific questionnaire with:

- A breadcrumb navigation (Dashboard > Questionnaires > Name)
- An "Add New Field" form with label, type (Text/Number), and category (PII Encrypted, Medical Encrypted, Demographic) dropdowns
- A table of existing fields showing label, type, category (with colour-coded badges), and a delete button

#### `client_view_submissions.html` - View Anonymised Submissions

Extends `base_client.html`. Displays anonymised submission data in a table:

- Breadcrumb navigation
- An info banner about GDPR-compliant anonymisation
- A count of active respondents
- A dynamic table with columns generated from the questionnaire fields and rows for each respondent (labelled "Respondent 1", "Respondent 2", etc.)
- Empty state if no submissions or all consent withdrawn

### Admin/Audit Pages

#### `audit_dashboard.html` - Audit Log Dashboard

Extends `base.html` directly (unique dark navbar, not using base_client). A comprehensive audit monitoring dashboard with:

- A custom dark navbar with back-to-dashboard link and client username
- **Statistics row**: Total log entries, successful logins, failed login attempts, data access events
- **Chain integrity status**: Shows whether the SHA-256 hash chain is VERIFIED or COMPROMISED, with a re-verify button
- **Filters**: Action type, actor type, and date range dropdowns with an Apply button
- **Activity Location Map**: An interactive Leaflet.js map. Clicking an IP address in the table geolocates it and shows a marker with city, country, and ISP info
- **Audit log table**: Paginated table showing log ID, timestamp, actor (type + ID), action (colour-coded badge), target table/ID, IP address (clickable for geolocation), and details (JSON)
- **Pagination**: Previous/Next with page numbers
- **Action summary**: Badge counts of each action type
- **Export CSV** button for downloading filtered logs

---

## Static Files

### `presentation/static/main.css` - Master Stylesheet

The single consolidated CSS file for the entire application (~3100+ lines). Organised into 23 sections:

1. **CSS Custom Properties** - Design tokens: colour palette (purple primary, semantic colours), spacing, radius, shadows, transitions, font family (Inter)
2. **Reset & Base** - Box-sizing reset, body styles with gradient background
3. **Animations** - `fadeInUp`, `fadeIn`, `slideIn`, `scaleIn`, `slideInUp` keyframes for page transitions
4. **Typography** - Heading styles
5. **Navbar** - Styles for all navbar variants (user, client, audit) with glassmorphism effects
6. **Auth Pages** - Centered auth card layout, background, input styles, buttons for login/register
7. **Flash Messages** - Alert styling for notifications
8. **Homepage** - User and client dashboard grid layouts, action cards with hover effects
9. **Content Pages** - Data display, page containers, info banners
10. **Cards** - Data cards with headers and bodies for displaying grouped information
11. **Tables** - Modern table styling with alternating rows
12. **Forms & Inputs** - Form controls, select dropdowns, checkboxes, consent checkboxes
13. **Buttons** - Primary, success, danger, secondary button styles
14. **Badges** - Status badges (active/withdrawn), action badges
15. **Audit Dashboard** - Dark theme overrides, stat cards, chain status indicators, filter form, map section, log table styles
16. **Container Overrides** - Container width adjustments
17. **Responsive Breakpoints** - Media queries for mobile, tablet, and desktop layouts
18. **Landing Page** - Full-page landing with data grid backgrounds, spotlight effects, hero section, login card, feature badges, parallax
19. **Client Landing Page** - Particle network background, glass morphism cards, gradient headlines, trust bar, ambient orbs, responsive adjustments
20. **Cookie/Privacy Banner** - Fixed bottom banner for cookie notice
21. **Privacy Policy Page** - Privacy-specific card layouts, rights grid, data category badges, responsive table
22. **Consent & Export Enhancements** - Status badge styles, export button, info banners
23. **User-Side Styles** - Enhanced user page theme with select cards, questionnaire form styles, empty states
24. **Client-Side Theme** - Client page colour overrides, action cards, info banners, form cards, breadcrumbs
25. **Additional Animations** - Extra animation keyframes

### `presentation/static/landing.js` - User Landing Page Animations

A self-contained JavaScript module (~300 lines) that creates the interactive data visualisation on the user landing page:

- **Fake donor records** - 30 realistic Irish donor records with names, Dublin addresses, ages, blood types, organs, and consent status
- **Data grid** - Renders the records as a scrollable grid of text in the background, showing field names and values
- **Encrypted grid** - Creates a second overlay grid where each value is replaced with fake pgcrypto-style hex strings (`\xc30d04...`)
- **Spotlight effect** - As the user moves their cursor, a radial gradient mask reveals the encrypted version of the data underneath, visually demonstrating what encryption looks like
- **Grid canvas** - Draws subtle animated grid lines that slowly drift
- **Cursor echo trails** - Canvas-based trailing circles that follow the cursor with fade-out effects
- **Parallax** - Subtle parallax movement on the hero text and login card as the cursor moves
- **Text colour inversion** - Elements near the spotlight invert to white for readability

### `presentation/static/client_landing.js` - Client Landing Page Animation

A self-contained JavaScript module (~120 lines) that creates the particle network animation on the client portal landing page:

- **Particle system** - 60 small dots floating around the page with random velocities
- **Connection lines** - When two particles are within 120px of each other, a faint connecting line is drawn between them, creating a network effect
- **Mouse interaction** - Particles near the mouse cursor are also connected to it with lines
- **Canvas management** - Handles high-DPI displays, window resizing, and animation loops
- **Performance** - Uses `requestAnimationFrame` for smooth 60fps animation

---

## Architecture Summary

The system follows a **3-tier architecture**:

1. **Presentation Layer** (`presentation/`) - HTML templates (Jinja2) + CSS + JS
2. **Application Layer** (`application/`) - Flask routes (controllers) + services (business logic)
3. **Data Layer** (`data/`) - Database operations (PostgreSQL with pgcrypto encryption)

**Two user types:**
- **Users** (donors) - Register, fill questionnaires, exercise GDPR rights
- **Clients** (organisations) - Create questionnaires, view anonymised data, monitor audit logs

**Security measures:**
- AES-256 encryption at rest for PII and Medical data (pgcrypto)
- PBKDF2 password hashing
- One-way hashing for Hashed category fields
- SHA-256 hash chain for tamper-evident audit logs
- JWT tokens for mobile API authentication
- Session-based authentication for web
- Ownership verification on all data access
