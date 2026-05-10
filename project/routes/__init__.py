import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()


def create_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "views"),
        static_folder=os.path.join(base_dir, "static"),
    )
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["DEBUG"] = os.getenv("DEBUG", "False").lower() == "true"
    CORS(app)
    from controllers.auth_controllers import auth_bp

    app.register_blueprint(auth_bp)
    return app
