from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

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