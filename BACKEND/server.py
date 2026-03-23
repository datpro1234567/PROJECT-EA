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
    userName = data.get("userName")
    password = data.get("password")

    con = sqlite3.connect("users.db")
    cursor = con.cursor()
    cursor.execute(
        """
        INSERT INTO user (name,password)
        VALUES (?, ?)
        """,
        (userName,password)
    )
    con.commit()
    con.close()

    return jsonify({"status":"store completely"})


server.run(debug = True)

# import CORS to allow client request through cross origin, request to get the incoming http request from client, use jsonfiy to convert the string then reponse the client