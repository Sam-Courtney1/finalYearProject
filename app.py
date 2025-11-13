from flask import Flask
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

    # Import Blueprints
    from application.routes.pages_and_actions import auth_bp, pages_bp
    from application.routes.questionnaire_routes import questionnaire_bp
    from application.routes.home_route import home_bp


    # Register Blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(questionnaire_bp)
    app.register_blueprint(home_bp)

    return app



if __name__ == "__main__":
    app = create_app()
    app.run(host = "0.0.0.0", port = 80, debug=True)


