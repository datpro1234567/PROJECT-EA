from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    # flash,
    session,
    jsonify,
    make_response,
)
from db import get_db_connection
from functools import wraps
from services.auth_services import (
    authenticate_user,
    create_user,
    check_user_exists,
    change_user_password,
)
from services.key_pair_services import (
    generate_root_ca_key_pair,
    generate_root_ca_certificate,
    generate_user_key_pair,
    get_user_key_pairs,
    get_user_private_key_pem,
)
from services.admin_monitoring_services import get_system_summary, list_recent_activity
from services.certificate_request_services import (
    create_issue_certificate_request,
    generate_csr_for_user_keypair,
    list_certificate_requests_for_admin,
    approve_certificate_request,
    approve_revoke_certificate_request,
    reject_certificate_request,
    create_revoke_certificate_request,
    list_revoked_certificates_system,
    list_certificates_for_user,
    get_user_certificate_pem,
)
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


@auth_bp.route("/api/user/keypair", methods=["POST"])
@login_required
def api_generate_user_keypair():
    """Generate a personal key pair for the currently logged-in user."""

    if session.get("role") != "customer":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Only customer users can generate personal key pairs.",
                }
            ),
            403,
        )

    user_id = session.get("user_id")
    success, message = generate_user_key_pair(user_id, owner_type="customer")
    status_code = 200 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@auth_bp.route("/api/user/keypairs", methods=["GET"])
@login_required
def api_list_user_keypairs():
    """Return all key pairs belonging to the current customer user."""

    if session.get("role") != "customer":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Only customer users can view personal key pairs.",
                }
            ),
            403,
        )

    user_id = session.get("user_id")
    success, data = get_user_key_pairs(int(user_id), owner_type="customer")

    if not success:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Could not load key pairs for this user.",
                }
            ),
            500,
        )

    return jsonify({"success": True, "keys": data}), 200


@auth_bp.route("/api/user/keypairs/<int:keypair_id>/private", methods=["GET"])
@login_required
def api_download_user_private_key(keypair_id: int):
    """Allow a customer to download their own private key as a PEM file."""

    if session.get("role") != "customer":
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Only customer users can download personal private keys.",
                }
            ),
            403,
        )

    user_id = session.get("user_id")
    success, payload = get_user_private_key_pem(int(user_id), int(keypair_id), owner_type="customer")

    if not success:
        if isinstance(payload, dict):
            http_status = int(payload.get("http_status") or 400)
            body = {
                "success": False,
                "message": payload.get("message") or "Download failed.",
            }
            if payload.get("error"):
                body["error"] = payload.get("error")
            return jsonify(body), http_status

        return jsonify({"success": False, "message": str(payload)}), 404

    private_pem = payload  # bytes
    response = make_response(private_pem)
    response.headers["Content-Type"] = "application/x-pem-file"
    response.headers["Content-Disposition"] = f"attachment; filename=private_key_{keypair_id}.pem"
    return response


@auth_bp.route("/certificate/request", methods=["GET"])
@login_required
def view_certificate_request():
    if session.get("role") != "customer":
        return redirect(url_for("auth.home"))

    user_id = session.get("user_id")
    success, keypairs = get_user_key_pairs(int(user_id), owner_type="customer")
    if not success:
        keypairs = []

    return render_template("request_certificate.html", keypairs=keypairs)


@auth_bp.route("/api/user/certificate-requests/issue", methods=["POST"])
@login_required
def api_create_issue_certificate_request():
    if session.get("role") != "customer":
        return (
            jsonify({"success": False, "message": "Only customer users can create certificate requests."}),
            403,
        )

    data = request.get_json(silent=True) or request.form
    domain_name = (data.get("domain_name") or "").strip()

    key_pair_id_raw = data.get("key_pair_id")
    try:
        key_pair_id = int(key_pair_id_raw)
    except Exception:
        return jsonify({"success": False, "message": "Key pair is required."}), 400

    private_key_pem = (data.get("private_key_pem") or "").strip()
    if not private_key_pem:
        upload = request.files.get("private_key_file")
        if upload:
            try:
                private_key_pem = upload.read().decode("utf-8", errors="ignore").strip()
            except Exception:
                private_key_pem = ""

    if not domain_name:
        return jsonify({"success": False, "message": "Domain name is required."}), 400

    if not private_key_pem:
        return jsonify({"success": False, "message": "Private key file is required."}), 400

    user_id = session.get("user_id")

    ok, csr_payload = generate_csr_for_user_keypair(
        int(user_id),
        int(key_pair_id),
        domain_name,
        private_key_pem=private_key_pem,
    )
    if not ok:
        return jsonify({"success": False, "message": str(csr_payload)}), 400

    csr_pem = str((csr_payload or {}).get("csr_pem") or "").strip()
    if not csr_pem:
        return jsonify({"success": False, "message": "Failed to generate CSR."}), 400

    success, payload = create_issue_certificate_request(
        int(user_id),
        int(key_pair_id),
        csr_pem=csr_pem,
    )

    if not success:
        return jsonify({"success": False, "message": str(payload)}), 400

    return (
        jsonify(
            {
                "success": True,
                "message": "Request created.",
                "data": {
                    **(payload or {}),
                    "csr_pem": csr_pem,
                    "domain_name": (csr_payload or {}).get("domain_name"),
                },
            }
        ),
        201,
    )


@auth_bp.route("/admin/certificate-requests", methods=["GET"])
@login_required
def view_admin_certificate_requests():
    if session.get("role") != "admin":
        return redirect(url_for("auth.home"))

    success, requests_list = list_certificate_requests_for_admin()
    if not success:
        requests_list = []

    return render_template("admin_certificate_requests.html", requests=requests_list)


@auth_bp.route("/admin/dashboard", methods=["GET"])
@login_required
def view_admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("auth.home"))

    ok_sum, summary = get_system_summary()
    if not ok_sum:
        summary = {}

    ok_act, activity = list_recent_activity(20)
    if not ok_act:
        activity = []

    return render_template("admin_dashboard.html", summary=summary, activity=activity)


@auth_bp.route("/certificate/revoke", methods=["GET"])
@login_required
def view_certificate_revoke_request():
    if session.get("role") != "customer":
        return redirect(url_for("auth.home"))

    user_id = session.get("user_id")
    success, certs = list_certificates_for_user(int(user_id))
    if not success:
        certs = []

    # Only allow requesting revocation for currently issued certificates
    issued = [c for c in (certs or []) if str(c.get("status") or "").lower() == "issued"]

    return render_template("revoke_certificate.html", certificates=issued)


@auth_bp.route("/api/user/certificate-requests/revoke", methods=["POST"])
@login_required
def api_create_revoke_certificate_request():
    if session.get("role") != "customer":
        return (
            jsonify({"success": False, "message": "Only customer users can create revocation requests."}),
            403,
        )

    data = request.get_json(silent=True) or request.form
    cert_id_raw = data.get("certificate_id") or data.get("certificateId")
    try:
        certificate_id = int(cert_id_raw)
    except Exception:
        return jsonify({"success": False, "message": "Certificate is required."}), 400

    reason = (data.get("reason") or data.get("note") or "").strip() or None

    user_id = session.get("user_id")
    success, payload = create_revoke_certificate_request(int(user_id), int(certificate_id), reason=reason)
    if not success:
        return jsonify({"success": False, "message": str(payload)}), 400

    return jsonify({"success": True, "message": "Revocation request created.", "data": payload}), 201


@auth_bp.route("/revocations", methods=["GET"])
@login_required
def view_revocation_list_system():
    success, items = list_revoked_certificates_system()
    if not success:
        items = []
    return render_template("revocation_list.html", items=items)


@auth_bp.route("/api/revocations", methods=["GET"])
@login_required
def api_list_revoked_certs_system():
    success, items = list_revoked_certificates_system()
    if not success:
        return jsonify({"success": False, "message": "Could not load revoked certificates."}), 500
    return jsonify({"success": True, "items": items}), 200


@auth_bp.route("/api/user/certificates", methods=["GET"])
@login_required
def api_list_user_certificates():
    if session.get("role") != "customer":
        return (
            jsonify({"success": False, "message": "Only customer users can view their certificates."}),
            403,
        )

    user_id = session.get("user_id")
    success, data = list_certificates_for_user(int(user_id))
    if not success:
        return jsonify({"success": False, "message": "Could not load certificates."}), 500

    return jsonify({"success": True, "certificates": data}), 200


@auth_bp.route("/api/user/certificates/<int:certificate_id>/download", methods=["GET"])
@login_required
def api_download_user_certificate(certificate_id: int):
    if session.get("role") != "customer":
        return (
            jsonify({"success": False, "message": "Only customer users can download certificates."}),
            403,
        )

    user_id = session.get("user_id")
    success, payload = get_user_certificate_pem(int(user_id), int(certificate_id))
    if not success:
        return jsonify({"success": False, "message": str(payload)}), 404

    pem_text = payload or ""
    response = make_response(pem_text)
    response.headers["Content-Type"] = "application/x-pem-file"
    response.headers["Content-Disposition"] = f"attachment; filename=certificate_{certificate_id}.pem"
    return response


@auth_bp.route("/api/admin/certificate-requests/<int:request_id>/approve", methods=["POST"])
@login_required
def api_admin_approve_certificate_request(request_id: int):
    if session.get("role") != "admin":
        return (
            jsonify({"success": False, "message": "You do not have permission to perform this action."}),
            403,
        )

    data = request.get_json(silent=True) or request.form
    review_note = (data.get("review_note") or data.get("note") or "").strip() or None

    admin_id = session.get("user_id")

    # Dispatch approve by request_type (issue vs revoke)
    conn = None
    cursor = None
    req_type = None
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT TOP 1 request_type
                FROM certificate_requests
                WHERE id = ?
                """,
                (int(request_id),),
            )
            rr = cursor.fetchone()
            req_type = (rr[0] if rr else None)
    except Exception:
        req_type = None
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    if str(req_type).lower() == "revoke":
        success, payload = approve_revoke_certificate_request(int(request_id), int(admin_id), review_note=review_note)
    else:
        success, payload = approve_certificate_request(int(request_id), int(admin_id), review_note=review_note)
    if not success:
        status = 404 if str(payload) == "Request not found." else 400
        return jsonify({"success": False, "message": str(payload)}), status

    return jsonify({"success": True, "message": "Approved.", "data": payload}), 200


@auth_bp.route("/api/admin/certificate-requests/<int:request_id>/reject", methods=["POST"])
@login_required
def api_admin_reject_certificate_request(request_id: int):
    if session.get("role") != "admin":
        return (
            jsonify({"success": False, "message": "You do not have permission to perform this action."}),
            403,
        )

    data = request.get_json(silent=True) or request.form
    review_note = (data.get("review_note") or data.get("note") or "").strip() or None

    admin_id = session.get("user_id")
    success, payload = reject_certificate_request(int(request_id), int(admin_id), review_note=review_note)
    if not success:
        status = 404 if str(payload) == "Request not found." else 400
        return jsonify({"success": False, "message": str(payload)}), status

    return jsonify({"success": True, "message": "Rejected.", "data": payload}), 200


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
    password = data.get("password") or ""

    # Note: email / confirm_password are intentionally not required.
    is_valid, errors = validate_signup_data(username, password)
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

    user_exists = check_user_exists(username)

    if user_exists is None:
        return jsonify({"success": False, "message": "Database connection error."}), 500

    if user_exists:
        return (
            jsonify({"success": False, "message": "Username already exists."}),
            409,
        )

    # Create user
    success = create_user(username, password)

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
