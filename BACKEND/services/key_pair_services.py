import os
from typing import Dict, Optional, Tuple

from db import get_db_connection

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet


def _load_system_settings(cursor) -> Optional[Dict]:

    cursor.execute(
        """
        SELECT TOP 1
            default_key_algorithm,
            default_hash_algorithm,
            default_key_size,
            default_validity_days
        FROM system_settings
        ORDER BY id
        """
    )
    row = cursor.fetchone()
    if not row:
        return None

    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def _encrypt_private_key_pem(private_pem: bytes) -> str:
    fernet_key = os.getenv("PRIVATE_KEY_ENCRYPTION_KEY")
    if not fernet_key:
        # Fallback to storing plain text PEM (NOT recommended for production)
        return private_pem.decode("utf-8")

    try:
        f = Fernet(fernet_key.encode("utf-8"))
        token = f.encrypt(private_pem)
        return token.decode("utf-8")
    except Exception as exc:  # noqa: F841
        # If encryption fails for any reason, fallback to plain text storage
        return private_pem.decode("utf-8")


def generate_root_ca_key_pair(admin_user_id: int) -> Tuple[bool, str]:

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    try:
        cursor = conn.cursor()

        # 1. Load system settings
        settings = _load_system_settings(cursor)
        if not settings:
            return False, "System settings not configured for key generation."

        algorithm = (settings.get("default_key_algorithm") or "RSA").upper()
        key_size = settings.get("default_key_size") or 2048

        # 2. Check existing active Root CA key pair
        cursor.execute(
            """
            SELECT TOP 1 id
            FROM key_pairs
            WHERE owner_type = ?
              AND purpose = ?
              AND status = 'active'
            ORDER BY id DESC
            """,
            ("root_ca", "Root CA key pair"),
        )
        existing = cursor.fetchone()
        if existing:
            return False, "A Root CA key pair already exists (with active status)."

        # 3. Generate key pair (currently only RSA is supported)
        if algorithm != "RSA":
            algorithm = "RSA"  # Fallback to RSA for now

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        private_encrypted = _encrypt_private_key_pem(private_pem)

        # 4. Insert into key_pairs
        cursor.execute(
            """
            INSERT INTO key_pairs (
                owner_user_id,
                owner_type,
                public_key,
                private_key_encrypted,
                algorithm,
                key_size,
                purpose,
                status
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,  # Root CA is a system-level key, not bound to a user
                "root_ca",
                public_pem.decode("utf-8"),
                private_encrypted,
                algorithm,
                int(key_size),
                "Root CA key pair",
                "active",
            ),
        )

        new_id_row = cursor.fetchone()
        conn.commit()

        new_id = new_id_row[0] if new_id_row else None
        msg = (
            f"Successfully generated Root CA key pair (key_pairs.id = {new_id})."
            if new_id is not None
            else "Successfully generated Root CA key pair."
        )
        return True, msg

    except Exception as exc:
        conn.rollback()
        return False, f"Error generating Root CA key pair: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()
