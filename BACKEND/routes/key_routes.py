from flask import Blueprint, request, jsonify

from services.key_service import generate_user_key, create_root_ca_key as create_root_ca_key_service

key_bp = Blueprint("keys", __name__)


@key_bp.route("/generate_key", methods=["POST"])
def generate_key():
	data = request.json
	user_id = data.get("user_id")

	result, status_code = generate_user_key(user_id)
	return jsonify(result), status_code


@key_bp.route("/create_root_ca_key", methods=["POST"])
def create_root_ca_key():
	result, status_code = create_root_ca_key_service()
	return jsonify(result), status_code

