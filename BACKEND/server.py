from flask import Flask,request,jsonify
from flask_cors import CORS
import sqlite3

server = Flask(__name__)
CORS(server)

def init_db():
    con = sqlite3.connect("database.db")
    cursor = con.cursor()
#####################
    # users
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
        email TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # user_keys
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_keys
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        key_type TEXT NOT NULL,
        key_pem TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    # csr_requests
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS csr_requests
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_key_id INTEGER,
        csr_pem TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(user_key_id) REFERENCES user_keys(id)
        )
        """
    )

    # certificates
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS certificates
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        user_key_id INTEGER,
        csr_id INTEGER,
        serial_number TEXT UNIQUE NOT NULL,
        cert_pem TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'valid',
        issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(user_key_id) REFERENCES user_keys(id),
        FOREIGN KEY(csr_id) REFERENCES csr_requests(id)
        )
        """
    )

    # revocation_requests
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS revocation_requests
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        certificate_id INTEGER NOT NULL,
        reason TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        processed_at DATETIME,
        FOREIGN KEY(certificate_id) REFERENCES certificates(id)
        )
        """
    )

    # certificate_revocation_list
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS certificate_revocation_list
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        certificate_id INTEGER NOT NULL,
        serial_number TEXT NOT NULL,
        revoked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        reason TEXT,
        FOREIGN KEY(certificate_id) REFERENCES certificates(id)
        )
        """
    )

    # system_config
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_config
        (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT
        )
        """
    )

    # ca_keys
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ca_keys
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        key_type TEXT NOT NULL,
        key_pem TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # logs
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logs
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
################
    con.commit()
    con.close()

init_db();

@server.route("/")
def home():
    return "HELLO"

@server.route("/submit",  methods = ["POST"])
def submit():
    data = request.json
    name = data.get("username")
    password = data.get("password_hash")
    full_name = data.get("full_name")

    con = sqlite3.connect("database.db", timeout=5)
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (name,)
    )
    user = cursor.fetchone()
    if user != None :
        con.close()
        return jsonify({"status":"failure"})

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (?, ?, ?, 'user')
        """,
        (name, password, full_name)
    )
    con.commit()
    con.close()

    return jsonify({"status":"success"})

@server.route("/vertify", methods = ["POST"])
def vetify():
    data = request.json
    name = data.get("username")
    password = data.get("password_hash")

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT id, full_name
        FROM users
        WHERE username = ? AND password_hash = ?
        """,
        (name,password)
    )
    user = cursor.fetchone()
    con.close()

    if user != None:
        return jsonify({"status": "success","id":user["id"], "full_name": user["full_name"]})
    return jsonify({"status":"failure"})

@server.route("/changePassword", methods = ["POST"])
def changePassword():
    data = request.json
    id = data.get("id")
    password = data.get("password_hash")

    con = sqlite3.connect("database.db")
    cursor = con.cursor()
    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE id = ?
        """,
        (password,id)
    )
    con.commit();
    con.close();
    return jsonify({"status":"success"})
    

server.run(debug = True)

#add path (/vetify)