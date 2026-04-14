from flask import (
    Blueprint,
    render_template,
    request,
    # redirect,
    # url_for,
    # flash,
    session,
    jsonify,
)
from services.auth_services import authenticate_user, create_user, check_user_exists
from validators import validate_signup_data, validate_signin_data

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signin", methods=["GET"])
def view_signin():
    return render_template("signin.html")


@auth_bp.route("/signup", methods=["GET"])
def view_signup():
    return render_template("signup.html")


@auth_bp.route("/api/signin", methods=["POST"])
def signin():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    auth_valid, errors = validate_signin_data(username, password)
    if not auth_valid:
        first_error = next(iter(errors.values()))
        return (
            jsonify(
                {
                    "success": False,
                    "message": first_error,
                    "errors": errors,
                }
            ),
            400,
        )

    # Authenticate user
    user = authenticate_user(username, password)

    if user:
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Login successful.",
                    "user": {
                        "username": user["username"],
                        "id": user["user_id"],
                        "role": user["role"],
                    },
                }
            ),
            200,
        )
    else:
        return (
            jsonify({"success": False, "message": "Invalid username or password."}),
            401,
        )


@auth_bp.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    is_valid, errors = validate_signup_data(username, email, password, confirm_password)
    if not is_valid:
        first_error = next(iter(errors.values()))
        return (
            jsonify(
                {
                    "success": False,
                    "message": first_error,
                    "errors": errors,
                }
            ),
            400,
        )

    user_exists = check_user_exists(username, email)

    if user_exists is None:
        return jsonify({"success": False, "message": "Database connection error."}), 500

    if user_exists:
        return (
            jsonify({"success": False, "message": "Username or email already exists."}),
            409,
        )

    # Create user
    success = create_user(username, email, password)

    if success:
        return (
            jsonify({"success": True, "message": "User created successfully."}),
            201,
        )
    else:
        return (
            jsonify({"success": False, "message": "Failed to create user."}),
            500,
        )
