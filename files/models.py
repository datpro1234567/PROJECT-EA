"""
models.py
Tất cả hàm CRUD tương tác với MySQL qua pyodbc.
Mỗi hàm tự lấy connection từ database.get_connection().
"""

import hashlib
import secrets
import datetime
from database import get_connection


# ══════════════════════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════════════════════

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False

def _row_to_dict(cursor, row) -> dict:
    """Chuyển pyodbc row → dict dùng tên cột."""
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))

def _fetchall_dict(cursor) -> list:
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def _fetchone_dict(cursor) -> dict | None:
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [col[0] for col in cursor.description]
    return dict(zip(cols, row))


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

def create_user(username: str, password: str, role: str,
                full_name: str = "", email: str = "") -> int:
    """Tạo user mới. Trả về user_id."""
    pw_hash = _hash_password(password)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (username, password_hash, role, full_name, email)
               VALUES (?, ?, ?, ?, ?)""",
            (username, pw_hash, role, full_name, email)
        )
        conn.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]


def authenticate_user(username: str, password: str) -> dict | None:
    """Xác thực login. Trả về dict user hoặc None."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,)
        )
        user = _fetchone_dict(cursor)
    if user and _verify_password(password, user["password_hash"]):
        return user
    return None


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return _fetchone_dict(cursor)


def get_all_users() -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, role, full_name, email, created_at, is_active FROM users ORDER BY created_at DESC"
        )
        return _fetchall_dict(cursor)


def change_password(user_id: int, new_password: str) -> bool:
    pw_hash = _hash_password(new_password)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (pw_hash, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def seed_admin_if_empty():
    """Tạo tài khoản admin mặc định nếu bảng users trống."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        count = cursor.fetchone()[0]
    if count == 0:
        create_user("admin", "Admin@123", "admin", "System Administrator", "admin@localhost")
        print("[seed] Tạo admin mặc định: admin / Admin@123")


# ══════════════════════════════════════════════════════════════════════════════
# ROOT CERTIFICATES
# ══════════════════════════════════════════════════════════════════════════════

def create_root_cert(common_name, serial_number, not_before, not_after,
                     public_key_pem, private_key_pem, cert_pem, created_by: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO root_certificates
               (common_name, serial_number, not_before, not_after,
                public_key_pem, private_key_pem, cert_pem, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (common_name, serial_number, not_before, not_after,
             public_key_pem, private_key_pem, cert_pem, created_by)
        )
        conn.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]


def get_all_root_certs() -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT rc.*, u.username AS creator
               FROM root_certificates rc
               JOIN users u ON rc.created_by = u.id
               ORDER BY rc.created_at DESC"""
        )
        return _fetchall_dict(cursor)


def get_root_cert_by_id(root_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM root_certificates WHERE id = ?", (root_id,)
        )
        return _fetchone_dict(cursor)


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICATE REQUESTS (CSR)
# ══════════════════════════════════════════════════════════════════════════════

def create_cert_request(user_id: int, domain: str, organization: str,
                        country: str, csr_pem: str, public_key_pem: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO certificate_requests
               (user_id, domain, organization, country, csr_pem, public_key_pem)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, domain, organization, country, csr_pem, public_key_pem)
        )
        conn.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]


def get_pending_requests() -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT cr.*, u.username, u.email
               FROM certificate_requests cr
               JOIN users u ON cr.user_id = u.id
               WHERE cr.status = 'pending'
               ORDER BY cr.submitted_at DESC"""
        )
        return _fetchall_dict(cursor)


def get_requests_by_user(user_id: int) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT cr.*, c.cert_pem, c.not_after AS cert_expiry
               FROM certificate_requests cr
               LEFT JOIN certificates c ON c.request_id = cr.id
               WHERE cr.user_id = ?
               ORDER BY cr.submitted_at DESC""",
            (user_id,)
        )
        return _fetchall_dict(cursor)


def get_request_by_id(req_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM certificate_requests WHERE id = ?", (req_id,)
        )
        return _fetchone_dict(cursor)


def approve_request(req_id: int, admin_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE certificate_requests
               SET status = 'approved', reviewed_at = NOW(), reviewed_by = ?
               WHERE id = ? AND status = 'pending'""",
            (admin_id, req_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def reject_request(req_id: int, admin_id: int, reason: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE certificate_requests
               SET status = 'rejected', reviewed_at = NOW(),
                   reviewed_by = ?, reject_reason = ?
               WHERE id = ? AND status = 'pending'""",
            (admin_id, reason, req_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_all_requests() -> list:
    """Admin xem tất cả yêu cầu."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT cr.*, u.username, u.email
               FROM certificate_requests cr
               JOIN users u ON cr.user_id = u.id
               ORDER BY cr.submitted_at DESC"""
        )
        return _fetchall_dict(cursor)


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICATES (đã cấp)
# ══════════════════════════════════════════════════════════════════════════════

def create_certificate(request_id: int, user_id: int, issued_by: int,
                       serial_number: str, common_name: str,
                       not_before, not_after, cert_pem: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO certificates
               (request_id, user_id, issued_by, serial_number, common_name,
                not_before, not_after, cert_pem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (request_id, user_id, issued_by, serial_number, common_name,
             not_before, not_after, cert_pem)
        )
        conn.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]


def get_certificates_by_user(user_id: int) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT c.*, rc.common_name AS ca_name
               FROM certificates c
               JOIN root_certificates rc ON c.issued_by = rc.id
               WHERE c.user_id = ?
               ORDER BY c.issued_at DESC""",
            (user_id,)
        )
        return _fetchall_dict(cursor)


def get_all_certificates() -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT c.*, u.username, u.email, rc.common_name AS ca_name
               FROM certificates c
               JOIN users u ON c.user_id = u.id
               JOIN root_certificates rc ON c.issued_by = rc.id
               ORDER BY c.issued_at DESC"""
        )
        return _fetchall_dict(cursor)


def revoke_certificate(cert_id: int, admin_id: int, reason: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        # Revoke certificate
        cursor.execute(
            """UPDATE certificates
               SET status = 'revoked', revoked_at = NOW(),
                   revoked_by = ?, revoke_reason = ?
               WHERE id = ? AND status = 'valid'""",
            (admin_id, reason, cert_id)
        )
        if cursor.rowcount > 0:
            # Cập nhật request tương ứng
            cursor.execute(
                """UPDATE certificate_requests cr
                   JOIN certificates c ON c.request_id = cr.id
                   SET cr.status = 'revoked'
                   WHERE c.id = ?""",
                (cert_id,)
            )
        conn.commit()
        return cursor.rowcount > 0


def get_certificate_by_id(cert_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT c.*, u.username, u.email, rc.common_name AS ca_name
               FROM certificates c
               JOIN users u ON c.user_id = u.id
               JOIN root_certificates rc ON c.issued_by = rc.id
               WHERE c.id = ?""",
            (cert_id,)
        )
        return _fetchone_dict(cursor)


def search_certificates(keyword: str) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        like = f"%{keyword}%"
        cursor.execute(
            """SELECT c.*, u.username, u.email
               FROM certificates c
               JOIN users u ON c.user_id = u.id
               WHERE c.common_name LIKE ? OR c.serial_number LIKE ? OR u.username LIKE ?
               ORDER BY c.issued_at DESC""",
            (like, like, like)
        )
        return _fetchall_dict(cursor)


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════════════════

def log_action(user_id, action: str, target_type: str = None,
               target_id: int = None, detail: str = None, ip: str = None):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO audit_logs
                   (user_id, action, target_type, target_id, detail, ip_address)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, action, target_type, target_id, detail, ip)
            )
            conn.commit()
    except Exception as e:
        print(f"[audit_log] Error: {e}")


def get_audit_logs(limit: int = 200) -> list:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT al.*, u.username
               FROM audit_logs al
               LEFT JOIN users u ON al.user_id = u.id
               ORDER BY al.created_at DESC
               LIMIT ?""",
            (limit,)
        )
        return _fetchall_dict(cursor)
