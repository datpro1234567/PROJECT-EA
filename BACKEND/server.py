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
        SELECT id
        FROM user
        WHERE name = ?
        """,
        (name,)
    )
    user = cursor.fetchone()
    if user != None :
        return jsonify({"status":"failure"})

    cursor.execute(
        """
        INSERT INTO user (name, password)
        VALUES (?, ?)
        """,
        (name,password)
    )
    con.commit()
    con.close()

    return jsonify({"status":"success"})

@server.route("/verify", methods = ["POST"]) # return status and ID of element that verified
def vetify():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    con = sqlite3.connect("users.db")
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT id
        FROM user
        WHERE name = ? AND password = ?
        """,
        (name,password)
    )
    user = cursor.fetchone()
    con.close()

    if user != None:
        return jsonify({"status": "success","id":user["id"]})
    return jsonify({"status":"failure"})

@server.route("/changePassword", methods = ["POST"])
def changePassword():
    data = request.json
    id = data.get("id")
    newPassword = data.get("newPassword")

    con = sqlite3.connect("users.db")
    cursor = con.cursor()
    cursor.execute(
        """
        UPDATE user
        SET password = ?
        WHERE id = ?
        """,
        (newPassword,id)
    )
    con.commit();
    con.close();
    return jsonify({"status":"success"})
    

server.run(debug = True)

#add path (/vetify)