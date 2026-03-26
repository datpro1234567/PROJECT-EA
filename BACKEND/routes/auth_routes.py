from flask import Blueprint, request, jsonify

from services.auth_service import register_user, verify_user, change_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/submit", methods=["POST"])
def submit():
    data = request.json
    name = data.get("username")
    password = data.get("password")
    full_name = data.get("full_name")

    result = register_user(name, password, full_name)
    return jsonify(result)


@auth_bp.route("/vertify", methods=["POST"])
def vetify():
    data = request.json
    name = data.get("username")
    password = data.get("password")

    result = verify_user(name, password)
    return jsonify(result)


@auth_bp.route("/changePassword", methods=["POST"])
def changePassword():
    data = request.json
    user_id = data.get("id")
    password = data.get("password")

    result = change_password(user_id, password)
    return jsonify(result)
