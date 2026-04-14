from flask import Flask
from flask_cors import CORS
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_app():
    app = Flask(__name__, template_folder="../views", static_folder="../static")

    # Cấu hình khóa bí mật từ environment variable
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    app.config["DEBUG"] = os.getenv("DEBUG", "False").lower() == "true"

    CORS(app)

    # Đăng ký Blueprint
    from controllers.auth_controllers import auth_bp

    app.register_blueprint(auth_bp)
    return app
