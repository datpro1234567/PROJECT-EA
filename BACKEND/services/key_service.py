import sqlite3
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def get_system_config() -> dict:
    """Load system configuration from system_config table as a dict."""
    con = sqlite3.connect("database.db")
    cursor = con.cursor()
    cursor.execute("SELECT key, value FROM system_config")
    rows = cursor.fetchall()
    con.close()
    return {key: value for key, value in rows}


def get_root_ca_passphrase() -> bytes:
    # TODO: sau này nên load từ biến môi trường hoặc secret manager !!!
    return b"change_this_root_ca_passphrase"


def generate_user_key(user_id: int) -> tuple[dict, int]:
    """Generate an RSA key pair for a user, store public key, return private key PEM.

    Returns (response_dict, http_status_code).
    """
    if not user_id:
        return {"status": "failure", "message": "user_id is required"}, 400

    config = get_system_config()
    key_algorithm = config.get("key_algorithm", "RSA")
    key_size = int(config.get("key_size", "2048"))

    if key_algorithm != "RSA":
        return {"status": "failure", "message": "Unsupported key_algorithm"}, 400

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    con = sqlite3.connect("database.db")
    cursor = con.cursor()
    cursor.execute(
        """
        INSERT INTO user_keys (user_id, key_pem)
        VALUES (?, ?)
        """,
        (user_id, public_pem.decode("utf-8")),
    )
    con.commit()
    con.close()

    return {
        "status": "success",
        "private_key_pem": private_pem.decode("utf-8"),
    }, 200


def create_root_ca_key() -> tuple[dict, int]:
    """Generate an encrypted RSA private key for the Root CA and store it in ca_keys.

    Returns (response_dict, http_status_code).
    """
    config = get_system_config()
    key_algorithm = config.get("key_algorithm", "RSA")
    key_size = int(config.get("key_size", "2048"))

    if key_algorithm != "RSA":
        return {"status": "failure", "message": "Unsupported key_algorithm for CA key"}, 400

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    passphrase = get_root_ca_passphrase()
    private_pem_encrypted = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
    )

    con = sqlite3.connect("database.db")
    cursor = con.cursor()

    cursor.execute(
        """
        UPDATE ca_keys
        SET is_active = 0
        WHERE is_active = 1
        """
    )

    cursor.execute(
        """
        INSERT INTO ca_keys (name, key_type, public_key_pem, encrypted_private_key_pem, is_active)
        VALUES (?, ?, ?, ?, 1)
        """,
        (
            "Root CA",
            "RSA",
            public_pem.decode("utf-8"),
            private_pem_encrypted.decode("utf-8"),
        ),
    )

    con.commit()
    con.close()

    return {"status": "success"}, 200
