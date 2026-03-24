import sqlite3
import os

DB_NAME = "database.db"

def init_db():
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"Deleted existing {DB_NAME}")
        except PermissionError:
            print(f"Could not delete {DB_NAME}, it might be in use.")
            return

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. USERS table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
        email TEXT,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. SYSTEM_CONFIG table
    c.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    # Insert default config if not exists
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('key_size', '2048')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('hash_algorithm', 'SHA256')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('validity_days', '365')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('encryption', 'RSA')")

    # 3. ROOT_CA table
    c.execute("""
    CREATE TABLE IF NOT EXISTS root_ca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        private_key_pem TEXT, 
        certificate_pem TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )
    """)

    # 4. CERTIFICATES table
    c.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        serial_number TEXT UNIQUE,
        common_name TEXT,
        not_before TIMESTAMP,
        not_after TIMESTAMP,
        pem_content TEXT,
        is_revoked BOOLEAN DEFAULT 0,
        revocation_reason TEXT,
        revocation_date TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # 5. CSR_REQUESTS table
    c.execute("""
    CREATE TABLE IF NOT EXISTS csr_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        domain TEXT,
        organization TEXT,
        country TEXT,
        state TEXT,
        email TEXT,
        public_key_pem TEXT,
        csr_pem TEXT,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # 6. REVOCATION_REQUESTS table
    c.execute("""
    CREATE TABLE IF NOT EXISTS revocation_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        certificate_id INTEGER,
        reason TEXT,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(certificate_id) REFERENCES certificates(id)
    )
    """)

    # 7. LOGS table
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Create default admin user (admin/admin)
    # Using plain text for now as per current project state, or we can use hashing if we update app.py
    # Let's insert a default admin.
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES ('admin', 'admin', 'admin')")

    conn.commit()
    conn.close()
    print("Database initialized with full schema!")

if __name__ == "__main__":
    init_db()
