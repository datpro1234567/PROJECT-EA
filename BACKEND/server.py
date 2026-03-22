from flask import Flask
import sqlite3

server = Flask(__name__)

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

server.run(debug = True)