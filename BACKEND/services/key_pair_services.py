import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from db import get_db_connection

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.fernet import Fernet
from cryptography.x509.oid import NameOID


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


def _decrypt_private_key_pem(private_encrypted: str) -> bytes:
    """Decrypt stored private key PEM if encrypted, otherwise return raw bytes.

    The corresponding encrypt helper may store either a Fernet token or plain
    text PEM. This function attempts Fernet decryption when the key is
    configured; if anything fails, it falls back to treating the value as
    plain PEM.
    """

    raw_bytes = private_encrypted.encode("utf-8")

    fernet_key = os.getenv("PRIVATE_KEY_ENCRYPTION_KEY")
    if not fernet_key:
        return raw_bytes

    try:
        f = Fernet(fernet_key.encode("utf-8"))
        return f.decrypt(raw_bytes)
    except Exception:  # noqa: F841
        # If decryption fails for any reason, assume it is plain PEM
        return raw_bytes


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


def _get_hash_algorithm(settings: Dict) -> hashes.HashAlgorithm:
    name = (settings.get("default_hash_algorithm") or "SHA256").upper()

    if "512" in name:
        return hashes.SHA512()
    if "384" in name:
        return hashes.SHA384()
    if "224" in name:
        return hashes.SHA224()
    # Fallback
    return hashes.SHA256()


def generate_root_ca_certificate(admin_user_id: int) -> Tuple[bool, str]:
    """Generate a self-signed Root CA certificate for the whole system.

    This uses the active Root CA key pair (owner_type = 'root_ca') and stores
    the certificate plus basic status / ownership information in the
    certificates-related tables.
    """

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    try:
        cursor = conn.cursor()

        # 1. Load system settings for hash algorithm and validity
        settings = _load_system_settings(cursor)
        if not settings:
            return False, "System settings not configured for certificate generation."

        # 2. Check if a Root CA certificate already exists (issued)
        cursor.execute(
            """
            SELECT TOP 1 c.id
            FROM certificates c
            INNER JOIN certificate_ownership co ON co.certificate_id = c.id
            INNER JOIN key_pairs kp ON co.key_pair_id = kp.id
            INNER JOIN certificate_status cs ON cs.certificate_id = c.id
            WHERE kp.owner_type = ?
              AND cs.status = 'issued'
            ORDER BY c.id DESC
            """,
            ("root_ca",),
        )
        existing = cursor.fetchone()
        if existing:
            return False, "A Root CA certificate already exists with status 'issued'."

        # 3. Load active Root CA key pair
        cursor.execute(
            """
            SELECT TOP 1 id, public_key, private_key_encrypted, algorithm, key_size
            FROM key_pairs
            WHERE owner_type = ?
              AND status = 'active'
            ORDER BY id DESC
            """,
            ("root_ca",),
        )
        row = cursor.fetchone()
        if not row:
            return False, "No active Root CA key pair found. Please generate Root CA key pair first."

        root_key_pair_id, public_pem_str, private_enc_str, algorithm, key_size = row

        algorithm = (algorithm or "RSA").upper()
        if algorithm != "RSA":
            # At the moment only RSA is supported for certificate generation
            algorithm = "RSA"

        private_pem = _decrypt_private_key_pem(private_enc_str)
        try:
            private_key = load_pem_private_key(private_pem, password=None)
        except Exception as exc:  # noqa: F841
            return False, "Cannot load Root CA private key from database."

        hash_algo = _get_hash_algorithm(settings)

        # 4. Build self-signed Root CA certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EA System"),
                x509.NameAttribute(NameOID.COMMON_NAME, "EA Root CA"),
            ]
        )

        # Serial number as random 64-bit integer
        serial_number = x509.random_serial_number()

        now = datetime.utcnow()
        validity_days = settings.get("default_validity_days") or 365
        not_before = now
        not_after = now + timedelta(days=int(validity_days))

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(serial_number)
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=True,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
        )

        certificate = builder.sign(private_key=private_key, algorithm=hash_algo)

        public_key_der = certificate.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        subject_dn = "CN=EA Root CA, O=EA System, C=VN"
        issuer_dn = subject_dn

        signature_algorithm_name = f"{hash_algo.name.upper()}with{algorithm}"

        # 5. Insert certificate record
        cursor.execute(
            """
            INSERT INTO certificates (
                version,
                serial_number,
                subject_dn,
                issuer_dn,
                valid_from,
                valid_to,
                public_key,
                issuer_unique_identifier,
                subject_unique_identifier,
                signature_value,
                signature_algorithm
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,  # X.509 v3
                str(serial_number),
                subject_dn,
                issuer_dn,
                not_before,
                not_after,
                public_key_der,
                None,
                None,
                certificate.signature,
                signature_algorithm_name,
            ),
        )

        new_cert_row = cursor.fetchone()
        if not new_cert_row:
            conn.rollback()
            return False, "Failed to insert Root CA certificate into database."

        certificate_id = new_cert_row[0]

        # 6. Insert initial status: issued
        cursor.execute(
            """
            INSERT INTO certificate_status (
                certificate_id,
                status,
                changed_by_admin_id,
                revocation_reason_code,
                crl_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                certificate_id,
                "issued",
                int(admin_user_id) if admin_user_id is not None else None,
                None,
                None,
            ),
        )

        # 7. Map ownership to the admin user and Root CA key pair
        cursor.execute(
            """
            INSERT INTO certificate_ownership (
                certificate_id,
                user_id,
                key_pair_id,
                request_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                certificate_id,
                int(admin_user_id) if admin_user_id is not None else 1,
                root_key_pair_id,
                None,
            ),
        )

        conn.commit()

        return (
            True,
            f"Successfully generated Root CA certificate (certificates.id = {certificate_id}).",
        )

    except Exception as exc:
        conn.rollback()
        return False, f"Error generating Root CA certificate: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()
