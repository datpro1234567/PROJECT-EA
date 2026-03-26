from flask import Flask
from flask_cors import CORS

from routes.auth_routes import auth_bp
from routes.key_routes import key_bp
from database.init_db import init_db


server = Flask(__name__)
CORS(server)


init_db()


@server.route("/")
def home():
    return "HELLO"


server.register_blueprint(auth_bp)
server.register_blueprint(key_bp)


if __name__ == "__main__":
    server.run(debug=True)
