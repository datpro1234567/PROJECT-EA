import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, List

from db import get_db_connection

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.fernet import Fernet
from cryptography.x509.oid import NameOID


ROOT_CA_PRIVATE_KEY_PEM_CACHE: Optional[str] = None


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


def get_system_settings() -> Tuple[bool, object]:
    """Return current global system settings (row id=1)."""

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()
        settings = _load_system_settings(cursor)
        if not settings:
            return False, "System settings not configured."
        # Normalize output
        settings["default_key_algorithm"] = (settings.get("default_key_algorithm") or "RSA").upper()
        settings["default_hash_algorithm"] = (settings.get("default_hash_algorithm") or "SHA256").upper()
        settings["default_key_size"] = int(settings.get("default_key_size") or 2048)
        settings["default_validity_days"] = int(settings.get("default_validity_days") or 365)
        return True, settings

    except Exception as exc:
        return False, f"Error loading system settings: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def update_system_settings(
    default_key_algorithm: str,
    default_hash_algorithm: str,
    default_key_size: int,
    default_validity_days: int,
) -> Tuple[bool, str]:
    """Update global system settings (row id=1)."""

    algo = (default_key_algorithm or "RSA").strip().upper()
    # Current implementation supports RSA only
    if algo != "RSA":
        return False, "Only RSA is supported currently."

    hash_name = (default_hash_algorithm or "SHA256").strip().upper()
    allowed_hash = {"SHA256", "SHA384", "SHA512", "SHA224"}
    if hash_name not in allowed_hash:
        return False, f"Invalid hash algorithm. Allowed: {', '.join(sorted(allowed_hash))}"

    try:
        key_size = int(default_key_size)
    except Exception:
        return False, "Invalid key size."

    if key_size not in (2048, 3072, 4096):
        return False, "Key size must be one of: 2048, 3072, 4096."

    try:
        validity_days = int(default_validity_days)
    except Exception:
        return False, "Invalid default validity days."

    if validity_days < 1 or validity_days > 3650:
        return False, "Default validity days must be between 1 and 3650."

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE system_settings
            SET
                default_key_algorithm = ?,
                default_hash_algorithm = ?,
                default_key_size = ?,
                default_validity_days = ?
            WHERE id = 1
            """,
            (algo, hash_name, int(key_size), int(validity_days)),
        )

        if cursor.rowcount == 0:
            # If the row does not exist (shouldn't happen if schema seeded), insert it.
            cursor.execute(
                """
                INSERT INTO system_settings (
                    id,
                    default_key_algorithm,
                    default_hash_algorithm,
                    default_key_size,
                    default_validity_days
                )
                VALUES (1, ?, ?, ?, ?)
                """,
                (algo, hash_name, int(key_size), int(validity_days)),
            )

        conn.commit()
        return True, "Saved system settings."

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error saving system settings: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def _encrypt_private_key_pem(private_pem: bytes) -> bytes:
    fernet_key = os.getenv("PRIVATE_KEY_ENCRYPTION_KEY")
    if not fernet_key:
        # Fallback to storing plain text PEM (NOT recommended for production)
        return private_pem

    try:
        f = Fernet(fernet_key.encode("utf-8"))
        token = f.encrypt(private_pem)
        return token
    except Exception as exc:  # noqa: F841
        # If encryption fails for any reason, fallback to plain text storage
        return private_pem


def _decrypt_private_key_pem(private_encrypted) -> bytes:

    if private_encrypted is None:
        return b""

    if isinstance(private_encrypted, str):
        raw_bytes = private_encrypted.encode("utf-8")
    else:
        raw_bytes = bytes(private_encrypted)

    fernet_key = os.getenv("PRIVATE_KEY_ENCRYPTION_KEY")
    if not fernet_key:
        return raw_bytes

    try:
        f = Fernet(fernet_key.encode("utf-8"))
        return f.decrypt(raw_bytes)
    except Exception:  # noqa: F841
        # If decryption fails for any reason, assume it is plain PEM
        return raw_bytes


def set_root_ca_private_key_pem(private_key_pem: str) -> None:
    global ROOT_CA_PRIVATE_KEY_PEM_CACHE
    ROOT_CA_PRIVATE_KEY_PEM_CACHE = (private_key_pem or "").strip() or None


def get_root_ca_private_key_pem() -> Optional[str]:
    return ROOT_CA_PRIVATE_KEY_PEM_CACHE


def generate_root_ca_key_pair(admin_user_id: int) -> Tuple[bool, Any]:

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

        set_root_ca_private_key_pem(private_pem.decode("utf-8"))

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

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
                None,  # Root CA private key is not stored in the database
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
        return True, {
            "key_pair_id": new_id,
            "private_key_pem": private_pem.decode("utf-8"),
            "public_key_pem": public_pem.decode("utf-8"),
            "algorithm": algorithm,
            "key_size": int(key_size),
            "message": msg,
        }

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


def generate_root_ca_certificate(admin_user_id: int, root_private_key_pem: str) -> Tuple[bool, str]:
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

        # 3. Load active Root CA key pair public key
        cursor.execute(
            """
            SELECT TOP 1 id, public_key, algorithm, key_size
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

        root_key_pair_id, public_pem_str, algorithm, key_size = row

        algorithm = (algorithm or "RSA").upper()
        if algorithm != "RSA":
            # At the moment only RSA is supported for certificate generation
            algorithm = "RSA"

        try:
            private_key_pem = (root_private_key_pem or "").strip()
            if not private_key_pem:
                return False, "Root CA private key file is required. Please upload the private key before creating the root certificate."

            private_key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        except Exception:
            return False, "Cannot load the uploaded Root CA private key."

        try:
            stored_public_key = serialization.load_pem_public_key(public_pem_str.encode("utf-8"))
            uploaded_public_key = private_key.public_key()
            if stored_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ) != uploaded_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ):
                return False, "The uploaded private key does not match the active Root CA public key."
            set_root_ca_private_key_pem(private_key_pem)
        except Exception:
            return False, "Cannot verify the uploaded Root CA private key against the stored public key."

        hash_algo = _get_hash_algorithm(settings)

        # 4. Build self-signed Root CA certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Good Web"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Good Web Root CA"),
            ]
        )

        # Serial number as random 64-bit integer unique in the database
        # !!unique 
        serial_number = x509.random_serial_number()

        now = datetime.utcnow()
        validity_days = settings.get("default_validity_days") or 365
        not_before = now
        not_after = now + timedelta(days=int(validity_days))

        # Build the certificate
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

		# Full PEM-encoded certificate for storage/download
        certificate_pem = certificate.public_bytes(
			encoding=serialization.Encoding.PEM
		).decode("utf-8")

        subject_dn = "CN=Good Web Root CA, O=Good Web, C=VN"
        issuer_dn = subject_dn

        signature_algorithm_name = f"{hash_algo.name.upper()}with{algorithm}"

        # 5. Insert certificate record (including PEM for later download)
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
                certificate_pem,
                issuer_unique_identifier,
                subject_unique_identifier,
                signature_value,
                signature_algorithm
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,  # X.509 v3
                str(serial_number),
                subject_dn,
                issuer_dn,
                not_before,
                not_after,
                public_key_der,
                certificate_pem,
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


def generate_user_key_pair(user_id: int, owner_type: str = "customer") -> Tuple[bool, any]:
    """Generate user key pair. Returns (True, dict) with key data and private_key_pem, or (False, error_msg)."""
    if owner_type not in {"admin", "customer"}:
        owner_type = "customer"

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

        # 2. Generate key pair (currently only RSA is supported)
        if algorithm != "RSA":
            algorithm = "RSA"

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=int(key_size))
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

        # 3. NOTE: Private key is NOT saved to database (security best practice)
        # The private_key_encrypted field will be NULL
        # Client must download and securely store the private key

        # 4. Insert into key_pairs with NULL private_key_encrypted
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
                int(user_id),
                owner_type,
                public_pem.decode("utf-8"),
                None,  # Private key NOT stored in DB
                algorithm,
                int(key_size),
                "User key pair",
                "active",
            ),
        )

        new_id_row = cursor.fetchone()
        conn.commit()

        new_id = new_id_row[0] if new_id_row else None
        msg = f"Successfully generated key pair for user (key_pairs.id = {new_id})."

        # Return dict with key data including private key for immediate download
        return True, {
            "key_pair_id": new_id,
            "private_key_pem": private_pem.decode("utf-8"),
            "public_key_pem": public_pem.decode("utf-8"),
            "algorithm": algorithm,
            "key_size": int(key_size),
            "message": msg,
        }

    except Exception as exc:
        conn.rollback()
        return False, f"Error generating user key pair: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def get_user_key_pairs(user_id: int, owner_type: str = "customer") -> Tuple[bool, List[Dict]]:
    """Return all key pairs for a given user and owner_type.
    
    Note: Private keys are not stored in the database, so they cannot be downloaded later.
    """

    if owner_type not in {"admin", "customer"}:
        owner_type = "customer"

    conn = get_db_connection()
    if not conn:
        return False, []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                public_key,
                algorithm,
                key_size,
                status
            FROM key_pairs
            WHERE owner_user_id = ?
              AND owner_type = ?
            ORDER BY id
            """,
            (int(user_id), owner_type),
        )

        rows = cursor.fetchall() or []
        columns = [col[0] for col in cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        return True, data

    except Exception as exc:  # noqa: F841
        return False, []

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def get_user_private_key_pem(
    user_id: int,
    key_pair_id: int,
    owner_type: str = "customer",
) -> Tuple[bool, object]:
    """Load and decrypt a user's private key PEM for one-time download.

    - First successful call returns the private key bytes and removes it from the database.
    - Subsequent calls return an "already downloaded" error.

    On success returns (True, private_pem_bytes).
    On failure returns (False, error_payload) where error_payload is either a string
    or a dict containing {error, message, http_status}.
    """

    if owner_type not in {"admin", "customer"}:
        owner_type = "customer"

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    try:
        cursor = conn.cursor()

        # Atomically consume the private key (return old value then delete it).
        private_enc = None
        try:
            cursor.execute(
                """
                UPDATE key_pairs
                SET private_key_encrypted = NULL
                OUTPUT DELETED.private_key_encrypted
                WHERE id = ?
                  AND owner_user_id = ?
                  AND owner_type = ?
                  AND private_key_encrypted IS NOT NULL
                  AND DATALENGTH(private_key_encrypted) > 0
                """,
                (int(key_pair_id), int(user_id), owner_type),
            )
            consumed = cursor.fetchone()
            if consumed and consumed[0] is not None:
                private_enc = consumed[0]
                conn.commit()
        except Exception:
            # If the database column is NOT NULL, fall back to wiping the bytes (0x) instead of NULL.
            try:
                conn.rollback()
            except Exception:
                pass

            cursor.execute(
                """
                UPDATE key_pairs
                SET private_key_encrypted = 0x
                OUTPUT DELETED.private_key_encrypted
                WHERE id = ?
                  AND owner_user_id = ?
                  AND owner_type = ?
                  AND DATALENGTH(private_key_encrypted) > 0
                """,
                (int(key_pair_id), int(user_id), owner_type),
            )
            consumed = cursor.fetchone()
            if consumed and consumed[0] is not None:
                private_enc = consumed[0]
                conn.commit()

        if private_enc is not None:
            private_pem = _decrypt_private_key_pem(private_enc)
            if not private_pem:
                return (
                    False,
                    {
                        "error": "not_available",
                        "message": "Private key is not available.",
                        "http_status": 404,
                    },
                )
            return True, private_pem

        # No rows consumed: check why (not found, no access, already downloaded).
        try:
            conn.rollback()
        except Exception:
            pass

        cursor.execute(
            """
            SELECT owner_user_id, owner_type, private_key_encrypted
            FROM key_pairs
            WHERE id = ?
            """,
            (int(key_pair_id),),
        )
        row = cursor.fetchone()
        if not row:
            return False, {"error": "not_found", "message": "Key pair not found.", "http_status": 404}

        owner_user_id, db_owner_type, existing_private = row
        if owner_user_id is None:
            return False, {"error": "forbidden", "message": "You do not have access to this key pair.", "http_status": 403}

        if int(owner_user_id) != int(user_id) or (db_owner_type or "").lower() != owner_type.lower():
            return False, {"error": "forbidden", "message": "You do not have access to this key pair.", "http_status": 403}

        # Owned by user: determine if already downloaded.
        has_bytes = False
        try:
            has_bytes = existing_private is not None and len(bytes(existing_private)) > 0
        except Exception:
            has_bytes = existing_private is not None

        if not has_bytes:
            return (
                False,
                {
                    "error": "already_downloaded",
                    "message": "Private key has already been downloaded.",
                    "http_status": 410,
                },
            )

        return (
            False,
            {
                "error": "download_failed",
                "message": "Unable to download private key. Please try again.",
                "http_status": 400,
            },
        )

    except Exception as exc:
        return False, f"Error loading private key: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()
