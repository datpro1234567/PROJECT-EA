import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from db import getConnection

def checkUser(name,password):
    con = getConnection()
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT ID
        FROM USERS
        WHERE NAME = ? AND PASSWORD = ?
        """,(name, password)
    )

    result = cursor.fetchone()
    con.close()

    return result

def addUser(name,password):
    con = getConnection()
    cursor = con.cursor()

    cursor.execute(
        """
        INSERT INTO USERS(name,password)
        VALUES(?,?)
        """,(name,password))
        
    con.commit()
    con.close()

def updatePassword(id, newPassword):
    con = getConnection()
    cursor = con.cursor()

    cursor.execute(
        """
        UPDATE USERS
        SET PASSWORD = ?
        WHERE ID = ?
        """, (newPassword, id)
    )
    con.commit()
    con.close()