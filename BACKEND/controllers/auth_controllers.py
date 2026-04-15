from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    # flash,
    session,
    jsonify,
)
from functools import wraps
from services.auth_services import (
    authenticate_user,
    create_user,
    check_user_exists,
    change_user_password,
)
from services.key_pair_services import generate_root_ca_key_pair, generate_root_ca_certificate
from validators import (
    validate_signup_data,
    validate_signin_data,
    validate_change_password_data,
)

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.view_signin"))
        return view_func(*args, **kwargs)

    return wrapped_view


@auth_bp.route("/", methods=["GET"])
@login_required
def home():
    return render_template("home.html")


@auth_bp.route("/api/admin/root-keypair", methods=["POST"])
@login_required
def api_generate_root_keypair():
    if session.get("role") != "admin":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to perform this action.",
                }
            ),
            403,
        )

    admin_id = session.get("user_id")
    success, message = generate_root_ca_key_pair(admin_id)
    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@auth_bp.route("/api/admin/root-certificate", methods=["POST"])
@login_required
def api_generate_root_certificate():
    if session.get("role") != "admin":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "You do not have permission to perform this action.",
                }
            ),
            403,
        )

    admin_id = session.get("user_id")
    success, message = generate_root_ca_certificate(admin_id)
    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@auth_bp.route("/api/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or request.form

    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = (
        data.get("confirm_password")
        or data.get("confirm-password")
        or ""
    )

    is_valid, errors = validate_change_password_data(
        old_password, new_password, confirm_password
    )
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

    user_id = session.get("user_id")
    result, message = change_user_password(user_id, old_password, new_password)

    if result is None:
        return (
            jsonify({"success": False, "message": message}),
            500,
        )
    if result is False:
        return (
            jsonify({"success": False, "message": message}),
            400,
        )

    return jsonify({"success": True, "message": message}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.view_signin"))


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
    # Hỗ trợ cả "confirm_password" (snake_case) và "confirm-password" (từ form HTML)
    confirm_password = (
        data.get("confirm_password")
        or data.get("confirm-password")
        or ""
    )

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

    # success is None: lỗi kết nối DB
    if success is None:
        return (
            jsonify({"success": False, "message": "Database connection error."}),
            500,
        )

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
