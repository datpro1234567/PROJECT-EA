import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from flask import request
from models.userModel import checkUser,addUser,updatePassword

def submit():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    result = checkUser(name, password)
    if result != None:
        return {"status":"failure"}
    
    addUser(name, password)
    return {"status":"success"}


def verify():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    result = checkUser(name, password)
    if result == None:
        return {"status":"failure"}
    return {"status": "success",  "id": result[0]}

def changePassword():
    data = request.json
    id = int(data.get("id"))
    newPassword = data.get("newPassword")

    updatePassword(id, newPassword)
    return {"status": "success"}

