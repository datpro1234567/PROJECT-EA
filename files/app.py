"""
app.py
Flask application chính — toàn bộ routing theo kiến trúc monolithic.
Chạy: python app.py
"""

import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_file, jsonify
)
import io

from database import init_db, get_connection
from models import (
    authenticate_user, create_user, get_user_by_id,
    get_all_users, change_password, seed_admin_if_empty,
    create_root_cert, get_all_root_certs, get_root_cert_by_id,
    create_cert_request, get_pending_requests, get_requests_by_user,
    get_request_by_id, approve_request, reject_request, get_all_requests,
    create_certificate, get_certificates_by_user, get_all_certificates,
    revoke_certificate, get_certificate_by_id, search_certificates,
    log_action, get_audit_logs
)
from crypto import create_root_ca, create_csr, sign_csr, cert_info

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "x509-secret-dev-key-change-in-prod")


# ══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Bạn không có quyền truy cập trang này.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return login_required(decorated)

def _current_user():
    return {
        "id":       session.get("user_id"),
        "username": session.get("username"),
        "role":     session.get("role"),
    }

def _log(action, target_type=None, target_id=None, detail=None):
    log_action(
        session.get("user_id"), action,
        target_type, target_id, detail,
        request.remote_addr
    )


# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = authenticate_user(username, password)
        if user:
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["role"]     = user["role"]
            _log("LOGIN")
            flash(f"Chào mừng, {user['full_name'] or user['username']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Tên đăng nhập hoặc mật khẩu không đúng.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    _log("LOGOUT")
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username  = request.form.get("username", "").strip()
        password  = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip()
        if not username or not password:
            flash("Vui lòng điền đầy đủ thông tin.", "warning")
        else:
            try:
                uid = create_user(username, password, "customer", full_name, email)
                _log("REGISTER", "user", uid)
                flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
                return redirect(url_for("login"))
            except Exception as e:
                flash(f"Lỗi: {str(e)}", "danger")
    return render_template("register.html")

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_pwd():
    if request.method == "POST":
        new_pw = request.form.get("new_password", "")
        if len(new_pw) < 6:
            flash("Mật khẩu phải có ít nhất 6 ký tự.", "warning")
        else:
            change_password(session["user_id"], new_pw)
            _log("CHANGE_PASSWORD")
            flash("Đổi mật khẩu thành công.", "success")
    return render_template("change_password.html", user=_current_user())


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    user = _current_user()
    if user["role"] == "admin":
        stats = {
            "total_users":    len(get_all_users()),
            "pending_reqs":   len(get_pending_requests()),
            "total_certs":    len(get_all_certificates()),
            "total_root_cas": len(get_all_root_certs()),
        }
        recent_logs = get_audit_logs(10)
        return render_template("dashboard_admin.html", user=user, stats=stats, logs=recent_logs)
    else:
        my_requests = get_requests_by_user(user["id"])
        my_certs    = get_certificates_by_user(user["id"])
        return render_template("dashboard_user.html", user=user,
                               requests=my_requests, certs=my_certs)


# ══════════════════════════════════════════════════════════════════════════════
# ROOT CA MANAGEMENT (admin only)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/root-ca")
@admin_required
def admin_root_ca():
    roots = get_all_root_certs()
    return render_template("admin_root_ca.html", user=_current_user(), roots=roots)

@app.route("/admin/root-ca/create", methods=["GET", "POST"])
@admin_required
def admin_create_root_ca():
    if request.method == "POST":
        cn   = request.form.get("common_name", "").strip()
        org  = request.form.get("organization", "X509 CA System").strip()
        days = int(request.form.get("validity_days", 3650))
        if not cn:
            flash("Common Name không được để trống.", "warning")
        else:
            try:
                result = create_root_ca(cn, org, validity_days=days)
                root_id = create_root_cert(
                    common_name    = cn,
                    serial_number  = result["serial_number"],
                    not_before     = result["not_before"],
                    not_after      = result["not_after"],
                    public_key_pem = result["public_key_pem"],
                    private_key_pem= result["private_key_pem"],
                    cert_pem       = result["cert_pem"],
                    created_by     = session["user_id"]
                )
                _log("CREATE_ROOT_CA", "root_cert", root_id, cn)
                flash(f"Tạo Root CA '{cn}' thành công!", "success")
                return redirect(url_for("admin_root_ca"))
            except Exception as e:
                flash(f"Lỗi tạo Root CA: {str(e)}", "danger")
    return render_template("admin_create_root_ca.html", user=_current_user())

@app.route("/admin/root-ca/<int:root_id>/download")
@admin_required
def download_root_cert(root_id):
    rc = get_root_cert_by_id(root_id)
    if not rc:
        flash("Không tìm thấy Root CA.", "danger")
        return redirect(url_for("admin_root_ca"))
    _log("DOWNLOAD_ROOT_CA", "root_cert", root_id)
    return send_file(
        io.BytesIO(rc["cert_pem"].encode()),
        as_attachment=True,
        download_name=f"root_ca_{rc['common_name'].replace(' ','_')}.pem",
        mimetype="application/x-pem-file"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICATE REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/request-cert", methods=["GET", "POST"])
@login_required
def request_cert():
    if request.method == "POST":
        domain   = request.form.get("domain", "").strip()
        org      = request.form.get("organization", "").strip()
        country  = request.form.get("country", "VN").strip()
        if not domain:
            flash("Tên miền không được để trống.", "warning")
        else:
            try:
                csr_data = create_csr(domain, org, country)
                req_id = create_cert_request(
                    user_id        = session["user_id"],
                    domain         = domain,
                    organization   = org,
                    country        = country,
                    csr_pem        = csr_data["csr_pem"],
                    public_key_pem = csr_data["public_key_pem"]
                )
                _log("SUBMIT_CSR", "cert_request", req_id, domain)
                flash("Yêu cầu đã được gửi! Vui lòng chờ admin duyệt.", "success")
                # Gửi private key về để user tải ngay
                session["last_private_key"] = csr_data["private_key_pem"]
                return redirect(url_for("download_private_key_page", req_id=req_id))
            except Exception as e:
                flash(f"Lỗi: {str(e)}", "danger")
    return render_template("request_cert.html", user=_current_user())

@app.route("/request-cert/<int:req_id>/private-key")
@login_required
def download_private_key_page(req_id):
    private_key = session.pop("last_private_key", None)
    return render_template("download_private_key.html",
                           user=_current_user(),
                           req_id=req_id,
                           private_key=private_key)

@app.route("/my-requests")
@login_required
def my_requests():
    reqs = get_requests_by_user(session["user_id"])
    return render_template("my_requests.html", user=_current_user(), requests=reqs)

@app.route("/my-certs")
@login_required
def my_certs():
    certs = get_certificates_by_user(session["user_id"])
    return render_template("my_certs.html", user=_current_user(), certs=certs)

@app.route("/my-certs/<int:cert_id>/download")
@login_required
def download_my_cert(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert or cert["user_id"] != session["user_id"]:
        flash("Không có quyền tải chứng nhận này.", "danger")
        return redirect(url_for("my_certs"))
    _log("DOWNLOAD_CERT", "certificate", cert_id)
    return send_file(
        io.BytesIO(cert["cert_pem"].encode()),
        as_attachment=True,
        download_name=f"cert_{cert['common_name'].replace(' ','_')}.pem",
        mimetype="application/x-pem-file"
    )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — DUYỆT / TỪ CHỐI YÊU CẦU
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/requests")
@admin_required
def admin_requests():
    status_filter = request.args.get("status", "all")
    if status_filter == "pending":
        reqs = get_pending_requests()
    else:
        reqs = get_all_requests()
    return render_template("admin_requests.html", user=_current_user(),
                           requests=reqs, status_filter=status_filter)

@app.route("/admin/requests/<int:req_id>")
@admin_required
def admin_request_detail(req_id):
    req   = get_request_by_id(req_id)
    roots = get_all_root_certs()
    if not req:
        flash("Không tìm thấy yêu cầu.", "danger")
        return redirect(url_for("admin_requests"))
    return render_template("admin_request_detail.html",
                           user=_current_user(), req=req, roots=roots)

@app.route("/admin/requests/<int:req_id>/approve", methods=["POST"])
@admin_required
def admin_approve(req_id):
    root_id = int(request.form.get("root_ca_id", 0))
    req = get_request_by_id(req_id)
    root = get_root_cert_by_id(root_id)
    if not req or not root:
        flash("Dữ liệu không hợp lệ.", "danger")
        return redirect(url_for("admin_requests"))
    try:
        signed = sign_csr(req["csr_pem"], root["cert_pem"], root["private_key_pem"])
        approve_request(req_id, session["user_id"])
        cert_id = create_certificate(
            request_id    = req_id,
            user_id       = req["user_id"],
            issued_by     = root_id,
            serial_number = signed["serial_number"],
            common_name   = req["domain"],
            not_before    = signed["not_before"],
            not_after     = signed["not_after"],
            cert_pem      = signed["cert_pem"]
        )
        _log("APPROVE_CERT", "certificate", cert_id, req["domain"])
        flash(f"Đã cấp chứng nhận cho '{req['domain']}'!", "success")
    except Exception as e:
        flash(f"Lỗi ký chứng nhận: {str(e)}", "danger")
    return redirect(url_for("admin_requests"))

@app.route("/admin/requests/<int:req_id>/reject", methods=["POST"])
@admin_required
def admin_reject(req_id):
    reason = request.form.get("reason", "").strip()
    reject_request(req_id, session["user_id"], reason)
    _log("REJECT_CERT", "cert_request", req_id, reason)
    flash("Đã từ chối yêu cầu.", "info")
    return redirect(url_for("admin_requests"))


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — QUẢN LÝ CHỨNG NHẬN
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/certificates")
@admin_required
def admin_certs():
    keyword = request.args.get("q", "").strip()
    certs = search_certificates(keyword) if keyword else get_all_certificates()
    return render_template("admin_certs.html", user=_current_user(),
                           certs=certs, keyword=keyword)

@app.route("/admin/certificates/<int:cert_id>")
@admin_required
def admin_cert_detail(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert:
        flash("Không tìm thấy chứng nhận.", "danger")
        return redirect(url_for("admin_certs"))
    info = cert_info(cert["cert_pem"])
    return render_template("admin_cert_detail.html",
                           user=_current_user(), cert=cert, info=info)

@app.route("/admin/certificates/<int:cert_id>/revoke", methods=["POST"])
@admin_required
def admin_revoke(cert_id):
    reason = request.form.get("reason", "Thu hồi bởi admin").strip()
    revoke_certificate(cert_id, session["user_id"], reason)
    _log("REVOKE_CERT", "certificate", cert_id, reason)
    flash("Đã thu hồi chứng nhận.", "warning")
    return redirect(url_for("admin_certs"))

@app.route("/admin/certificates/<int:cert_id>/download")
@admin_required
def admin_download_cert(cert_id):
    cert = get_certificate_by_id(cert_id)
    if not cert:
        flash("Không tìm thấy chứng nhận.", "danger")
        return redirect(url_for("admin_certs"))
    _log("ADMIN_DOWNLOAD_CERT", "certificate", cert_id)
    return send_file(
        io.BytesIO(cert["cert_pem"].encode()),
        as_attachment=True,
        download_name=f"cert_{cert['common_name'].replace(' ','_')}.pem",
        mimetype="application/x-pem-file"
    )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — QUẢN LÝ NGƯỜI DÙNG
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/users")
@admin_required
def admin_users():
    users = get_all_users()
    return render_template("admin_users.html", user=_current_user(), users=users)

@app.route("/admin/users/create", methods=["GET", "POST"])
@admin_required
def admin_create_user():
    if request.method == "POST":
        username  = request.form.get("username", "").strip()
        password  = request.form.get("password", "")
        role      = request.form.get("role", "customer")
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip()
        try:
            uid = create_user(username, password, role, full_name, email)
            _log("CREATE_USER", "user", uid, f"{username}/{role}")
            flash(f"Tạo tài khoản '{username}' thành công.", "success")
            return redirect(url_for("admin_users"))
        except Exception as e:
            flash(f"Lỗi: {str(e)}", "danger")
    return render_template("admin_create_user.html", user=_current_user())


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/logs")
@admin_required
def admin_logs():
    logs = get_audit_logs(500)
    return render_template("admin_logs.html", user=_current_user(), logs=logs)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC — XEM CHỨNG NHẬN (không cần đăng nhập)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/verify/<int:cert_id>")
def verify_cert(cert_id):
    cert = get_certificate_by_id(cert_id)
    info = cert_info(cert["cert_pem"]) if cert else None
    return render_template("verify_cert.html", cert=cert, info=info)


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("[startup] Khởi tạo database...")
    init_db()
    seed_admin_if_empty()
    print("[startup] Khởi động Flask server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
