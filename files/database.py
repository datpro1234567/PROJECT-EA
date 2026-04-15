"""
database.py
Kết nối MySQL qua pyodbc và khởi tạo schema.
Đổi DRIVER, SERVER, USER, PASSWORD cho phù hợp môi trường local.
"""

import pyodbc
import os

# ── Cấu hình kết nối ──────────────────────────────────────────────────────────
DB_CONFIG = {
    "driver":   os.getenv("DB_DRIVER",   "MySQL ODBC 8.0 Unicode Driver"),
    "server":   os.getenv("DB_SERVER",   "localhost"),
    "port":     os.getenv("DB_PORT",     "3306"),
    "database": os.getenv("DB_NAME",     "x509_ca"),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

def get_connection():
    """Trả về một connection pyodbc mới."""
    conn_str = (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['user']};"
        f"PWD={DB_CONFIG['password']};"
        "charset=utf8mb4;"
    )
    return pyodbc.connect(conn_str, autocommit=False)


# ── Schema SQL ────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
-- Tạo database nếu chưa có
CREATE DATABASE IF NOT EXISTS x509_ca
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE x509_ca;

-- Bảng người dùng hệ thống
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role          ENUM('admin', 'customer') NOT NULL DEFAULT 'customer',
    full_name     VARCHAR(128),
    email         VARCHAR(128) UNIQUE,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active     TINYINT(1) DEFAULT 1
);

-- Bảng Root CA (level 0) — chỉ admin tạo
CREATE TABLE IF NOT EXISTS root_certificates (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    common_name     VARCHAR(128) NOT NULL,
    serial_number   VARCHAR(64)  NOT NULL UNIQUE,
    not_before      DATETIME     NOT NULL,
    not_after       DATETIME     NOT NULL,
    public_key_pem  TEXT         NOT NULL,
    private_key_pem TEXT         NOT NULL,   -- lưu mã hóa
    cert_pem        TEXT         NOT NULL,
    created_by      INT          NOT NULL,   -- FK → users.id
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Bảng yêu cầu cấp chứng nhận (CSR)
CREATE TABLE IF NOT EXISTS certificate_requests (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT          NOT NULL,
    domain        VARCHAR(256) NOT NULL,     -- CN / SAN domain
    organization  VARCHAR(128),
    country       CHAR(2)      DEFAULT 'VN',
    csr_pem       TEXT         NOT NULL,
    public_key_pem TEXT        NOT NULL,
    status        ENUM('pending','approved','rejected','revoked') DEFAULT 'pending',
    reject_reason VARCHAR(256),
    submitted_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at   DATETIME,
    reviewed_by   INT,                       -- FK → users.id (admin)
    FOREIGN KEY (user_id)    REFERENCES users(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
);

-- Bảng chứng nhận đã cấp
CREATE TABLE IF NOT EXISTS certificates (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    request_id       INT          NOT NULL UNIQUE,
    user_id          INT          NOT NULL,
    issued_by        INT          NOT NULL,   -- FK → root_certificates.id
    serial_number    VARCHAR(64)  NOT NULL UNIQUE,
    common_name      VARCHAR(256) NOT NULL,
    not_before       DATETIME     NOT NULL,
    not_after        DATETIME     NOT NULL,
    cert_pem         TEXT         NOT NULL,
    status           ENUM('valid','revoked','expired') DEFAULT 'valid',
    revoke_reason    VARCHAR(256),
    revoked_at       DATETIME,
    revoked_by       INT,                     -- FK → users.id (admin)
    issued_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id)  REFERENCES certificate_requests(id),
    FOREIGN KEY (user_id)     REFERENCES users(id),
    FOREIGN KEY (issued_by)   REFERENCES root_certificates(id),
    FOREIGN KEY (revoked_by)  REFERENCES users(id)
);

-- Bảng audit log (theo dõi hoạt động)
CREATE TABLE IF NOT EXISTS audit_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    action      VARCHAR(128) NOT NULL,
    target_type VARCHAR(64),
    target_id   INT,
    detail      TEXT,
    ip_address  VARCHAR(64),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def init_db():
    """
    Khởi tạo schema lần đầu.
    Kết nối không có tên database trước, sau đó chạy script.
    """
    # Kết nối không chỉ định database để tạo DB mới
    conn_str = (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};"
        f"UID={DB_CONFIG['user']};"
        f"PWD={DB_CONFIG['password']};"
        "charset=utf8mb4;"
    )
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()

    # Chạy từng lệnh SQL (tách bởi dấu ;)
    for statement in SCHEMA_SQL.split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"[init_db] Warning: {e}")

    cursor.close()
    conn.close()
    print("[init_db] Schema đã được khởi tạo.")


if __name__ == "__main__":
    init_db()
