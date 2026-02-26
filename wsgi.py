from flask import Flask, session, redirect, url_for, flash
from flask_cors import CORS
from dotenv import load_dotenv
import os
import time
from datetime import timedelta

"""
This is the main file for the system and is where the 
Flask entry point is declared, env variables are imported 
and where flask is told where to find the HTML templates 
and static file ie css

Blueprints are Imported and then registered 
Blueprints are a collection of routes
Once delcared here they can be used anywhere in the system to call
functions and new pages such as login or homapage
"""

def create_app():
    load_dotenv()
    app = Flask(__name__,
                template_folder = os.path.join('presentation', 'templates'),
                static_folder = os.path.join('presentation', 'static')
                )
    app.secret_key = os.getenv("APP_ENC_KEY", "test")
    # Sessions marked permanent will expire after this duration of inactivity
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

    # Allows the mobile app to make requests to /api/ routes from a different device
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Import Blueprints
    from application.routes.pages_and_actions import auth_bp, pages_bp
    from application.routes.questionnaire_routes import questionnaire_bp
    from application.routes.home_route import home_bp
    from application.routes.client_routes import client_bp
    from application.routes.admin_routes import admin_bp

    # Register Blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(questionnaire_bp)
    app.register_blueprint(home_bp)
    # Client routes are prefixed with /client
    app.register_blueprint(client_bp, url_prefix='/client')
    # Admin routes for audit dashboard, prefixed with /admin
    app.register_blueprint(admin_bp, url_prefix='/admin')
    # Mobile app API routes, all start with /api/
    from application.routes.api_routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Lightweight keep-alive endpoint hit by the "Stay Logged In" button in base_user.html.
    # The before_request hook below updates last_activity when this route is called.
    @app.route('/ping')
    def ping():
        from flask import jsonify
        return jsonify({'ok': True})

    # Inactivity session timeout — checked on every request for logged-in users.
    # The JavaScript timer in base_user.html warns at 9 min and redirects at 10 min,
    # but this server-side check is the authoritative enforcement.
    SESSION_TIMEOUT_SECONDS = 600  # 10 minutes

    @app.before_request
    def check_session_timeout():
        # Only applies to fully-authenticated users (not pending 2FA or api tokens)
        if 'user_id' not in session:
            return
        last = session.get('last_activity')
        now = time.time()
        if last and (now - last) > SESSION_TIMEOUT_SECONDS:
            session.clear()
            flash('You were logged out due to 10 minutes of inactivity.', 'warning')
            return redirect(url_for('auth_bp.login_page'))
        session['last_activity'] = now
        session.modified = True

    # Initialize audit logging table
    # The function called executes sql to create the table
    # only if it does not exist yet
    from data.audit_database import create_audit_table
    create_audit_table()

    # Run database migrations for new columns
    # This will again execute sql if tables or rows don't exist
    from data.migrations import run_migrations
    run_migrations()

    return app


application = create_app()

# Only executes when ran locally
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    application.run(host="0.0.0.0", port=port, debug=True)