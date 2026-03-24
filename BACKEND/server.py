from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_cors import CORS
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
import os
import sqlite3

app = Flask(__name__)

# Allow requests from frontend (Vite dev server runs on 5173)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})

CERTS_DIR = "certs"


@app.route("/test", methods=["GET"])
def health_check():
	print("test ok")
	return jsonify({"status": "ok", "service": "x509-backend"})

#add path (/vetify)
if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)
