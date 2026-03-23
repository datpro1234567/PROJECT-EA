from flask import Flask,request,jsonify
from flask_cors import CORS
import sqlite3

server = Flask(__name__)
CORS(server)

def init_db():
    con = sqlite3.connect("users.db")
    cursor = con.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user
        (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        password TEXT
        )
        """
    )
    con.commit()
    con.close()

init_db();

@server.route("/")
def home():
    return "HELLO"

@server.route("/submit",  methods = ["POST"])
def submit():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    con = sqlite3.connect("users.db")
    cursor = con.cursor()
    cursor.execute(
        """
        INSERT INTO user (name, password)
        VALUES (?, ?)
        """,
        (name,password)
    )
    con.commit()
    con.close()

    return jsonify({"status":"store completely"})

@server.route("/vertify", methods = ["POST"])
def vetify():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    con = sqlite3.connect("users.db")
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT id
        FROM user
        WHERE name = ? and password = ? 
        """,
        (name, password)
    )
    user = cursor.fetchone()
    con.close()

    if user != None:
        return jsonify({"status": "allow"})
    return jsonify({"status":"deny"})


server.run(debug = True)

#add path (/vetify)