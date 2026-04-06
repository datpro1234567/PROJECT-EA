from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from services.userService import submit, verify, changePassword
server = Flask(__name__)
CORS(server)

@server.route("/submit", methods = ("POST",))
def submit_route():
    return jsonify(submit())


@server.route("/verify", methods = ("POST",))
def verify_route():
    return jsonify(verify())    

@server.route("/changePassword", methods = ("POST",))
def changePassword_route():
    return jsonify(changePassword())    