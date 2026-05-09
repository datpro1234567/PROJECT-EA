from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from db import get_db_connection
from services.key_pair_services import (
    _decrypt_private_key_pem,
    _get_hash_algorithm,
    _load_system_settings,
)


def create_issue_certificate_request(
    user_id: int,
    key_pair_id: int,
    csr_pem: str,
) -> Tuple[bool, object]:
    """Create a new certificate issue request for a customer user."""

    csr_clean = (csr_pem or "").strip()
    if not csr_clean:
        return False, "CSR is required."

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()

        # Ensure key pair belongs to this user + load public key
        cursor.execute(
            """
            SELECT TOP 1 id, public_key
            FROM key_pairs
            WHERE id = ?
              AND owner_user_id = ?
              AND owner_type = ?
            """,
            (int(key_pair_id), int(user_id), "customer"),
        )
        row = cursor.fetchone()
        if not row:
            return False, "Invalid key pair."

        _kp_id, public_pem_str = row
        public_pem_bytes = (public_pem_str or "").encode("utf-8")
        try:
            user_public_key = serialization.load_pem_public_key(public_pem_bytes)
        except Exception as exc:
            return False, f"Cannot load user public key: {exc}"

        # Parse/validate CSR
        try:
            csr_obj = x509.load_pem_x509_csr(csr_clean.encode("utf-8"))
        except Exception as exc:
            return False, f"Invalid CSR: {exc}"

        # Verify CSR signature if supported by installed cryptography
        try:
            is_valid_sig = getattr(csr_obj, "is_signature_valid", None)
            if is_valid_sig is False:
                return False, "Invalid CSR signature."
        except Exception:
            pass

        # Ensure CSR public key matches the selected key pair
        try:
            csr_pub_der = csr_obj.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            kp_pub_der = user_public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            if csr_pub_der != kp_pub_der:
                return False, "CSR public key does not match selected key pair."
        except Exception as exc:
            return False, f"Cannot verify CSR public key: {exc}"

        # Extract domain from CSR (prefer SAN DNSName, else CN)
        domain_name: Optional[str] = None
        try:
            san_ext = csr_obj.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            dns_names = san_ext.value.get_values_for_type(x509.DNSName)
            if dns_names:
                domain_name = (dns_names[0] or "").strip() or None
        except Exception:
            pass

        if not domain_name:
            try:
                cn_attrs = csr_obj.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                if cn_attrs:
                    domain_name = (cn_attrs[0].value or "").strip() or None
            except Exception:
                pass

        if not domain_name:
            return False, "CSR must include a domain (SAN DNSName or Subject CN)."

        cursor.execute(
            """
            INSERT INTO certificate_requests (
                user_id,
                certificate_id,
                key_pair_id,
                request_type,
                request_status,
                csr_pem,
                domain_name,
                reason
            )
            OUTPUT INSERTED.id
            VALUES (?, NULL, ?, 'issue', 'pending', ?, ?, NULL)
            """,
            (
                int(user_id),
                int(key_pair_id),
                csr_clean,
                str(domain_name),
            ),
        )

        new_row = cursor.fetchone()
        conn.commit()

        new_id = new_row[0] if new_row else None
        if new_id is None:
            return False, "Failed to create request."

        return True, {"request_id": int(new_id)}

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error creating request: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def generate_csr_for_user_keypair(
    user_id: int,
    key_pair_id: int,
    domain_name: str,
    private_key_pem: str,
    subject_o: Optional[str] = None,
    subject_c: Optional[str] = None,
) -> Tuple[bool, object]:
    """Generate a CSR for a user's selected keypair using an uploaded private key.

    Validates:
    - keypair belongs to user
    - uploaded private key matches the stored public key
    """

    domain = (domain_name or "").strip()
    if not domain:
        return False, "Domain name is required."

    org = (subject_o or "").strip()
    if not org:
        return False, "Organization (Subject O) is required."

    country = (subject_c or "").strip().upper()
    if not country:
        return False, "Country code (Subject C) is required."
    if len(country) != 2 or not country.isalpha():
        return False, "Country code (Subject C) must be 2 letters (e.g., VN, US)."

    private_text = (private_key_pem or "").strip()
    if not private_text:
        return False, "Private key is required."

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT TOP 1 public_key
            FROM key_pairs
            WHERE id = ?
              AND owner_user_id = ?
              AND owner_type = ?
            """,
            (int(key_pair_id), int(user_id), "customer"),
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return False, "Invalid key pair."

        public_pem_bytes = str(row[0]).encode("utf-8")
        try:
            user_public_key = serialization.load_pem_public_key(public_pem_bytes)
        except Exception as exc:
            return False, f"Cannot load stored public key: {exc}"

        private_pem_bytes = private_text.encode("utf-8")
        try:
            private_key = load_pem_private_key(private_pem_bytes, password=None)
        except TypeError:
            return False, "Encrypted private key is not supported. Please upload an unencrypted PEM key."
        except Exception as exc:
            return False, f"Invalid private key: {exc}"

        try:
            priv_pub_der = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            kp_pub_der = user_public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            if priv_pub_der != kp_pub_der:
                return False, "Private key does not match the selected public key (key pair)."
        except Exception as exc:
            return False, f"Cannot verify private/public key match: {exc}"

        # Prefer system-configured hash algorithm if available
        try:
            settings = _load_system_settings(cursor)
            csr_hash_algo = _get_hash_algorithm(settings or {})
        except Exception:
            csr_hash_algo = hashes.SHA256()

        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
                x509.NameAttribute(NameOID.COMMON_NAME, domain),
            ]
        )

        csr = (
            x509.CertificateSigningRequestBuilder()
            .subject_name(subject)
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(domain)]),
                critical=False,
            )
            .sign(private_key, csr_hash_algo)
        )

        csr_pem_out = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        return True, {"csr_pem": csr_pem_out, "domain_name": domain}

    except Exception as exc:
        return False, f"Error generating CSR: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def list_certificate_requests_for_admin() -> Tuple[bool, List[Dict]]:
    """List certificate requests for admin view."""

    conn = get_db_connection()
    if not conn:
        return False, []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                r.id,
                u.username,
                r.request_type,
                r.request_status,
                r.domain_name,
                r.key_pair_id,
                r.reason,
                r.submitted_at,
                r.reviewed_at,
                r.review_note
            FROM certificate_requests r
            INNER JOIN users u ON u.id = r.user_id
            ORDER BY r.submitted_at DESC, r.id DESC
            """
        )

        rows = cursor.fetchall() or []
        columns = [col[0] for col in cursor.description]
        return True, [dict(zip(columns, row)) for row in rows]

    except Exception:
        return False, []

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def _review_request(
    request_id: int,
    admin_id: int,
    new_status: str,
    review_note: Optional[str] = None,
) -> Tuple[bool, object]:
    """Approve/reject a certificate request.

    Only requests in 'pending' state can be reviewed.
    """

    if new_status not in {"approved", "rejected"}:
        return False, "Invalid status."

    note = (review_note or "").strip() or None

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE certificate_requests
            SET request_status = ?,
                reviewed_at = SYSDATETIME(),
                reviewed_by_admin_id = ?,
                review_note = ?
            OUTPUT INSERTED.id, INSERTED.request_status
            WHERE id = ?
              AND request_status = 'pending'
            """,
            (
                new_status,
                int(admin_id),
                note,
                int(request_id),
            ),
        )

        row = cursor.fetchone()
        if not row:
            # Distinguish not-found vs already-reviewed
            cursor.execute(
                """
                SELECT request_status
                FROM certificate_requests
                WHERE id = ?
                """,
                (int(request_id),),
            )
            existing = cursor.fetchone()
            if not existing:
                return False, "Request not found."
            return False, f"Request has already been processed (status: {existing[0]})."

        conn.commit()
        return True, {"request_id": int(row[0]), "status": str(row[1])}

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error reviewing request: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def approve_certificate_request(
    request_id: int,
    admin_id: int,
    review_note: Optional[str] = None,
) -> Tuple[bool, object]:
    """Approve an issue request and immediately issue a certificate.

    This is "option 2": approve == issue.

    Requirements:
    - Root CA key pair exists and is active
    - Root CA certificate exists with status 'issued'

    On success:
    - Inserts new certificate + status
    - Inserts certificate ownership
    - Updates request to request_status='completed' and sets certificate_id
    """

    note = (review_note or "").strip() or None

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    try:
        cursor = conn.cursor()

        settings = _load_system_settings(cursor)
        if not settings:
            return False, "System settings not configured for certificate generation."

        # Ensure Root CA certificate exists
        cursor.execute(
            """
            SELECT TOP 1 c.id, c.certificate_pem
            FROM certificates c
            INNER JOIN certificate_ownership co ON co.certificate_id = c.id
            INNER JOIN key_pairs kp ON kp.id = co.key_pair_id
            INNER JOIN certificate_status cs ON cs.certificate_id = c.id
            WHERE kp.owner_type = ?
              AND cs.status = 'issued'
            ORDER BY c.id DESC
            """,
            ("root_ca",),
        )
        root_cert_row = cursor.fetchone()
        if not root_cert_row:
            return False, "Root CA certificate not found. Please create Root CA certificate first."

        root_cert_id, _root_cert_pem = root_cert_row

        # Load active Root CA key pair (must have private key for signing)
        cursor.execute(
            """
            SELECT TOP 1 id, private_key_encrypted, algorithm
            FROM key_pairs
            WHERE owner_type = ?
              AND status = 'active'
            ORDER BY id DESC
            """,
            ("root_ca",),
        )
        root_kp_row = cursor.fetchone()
        if not root_kp_row:
            return False, "No active Root CA key pair found. Please generate Root CA key pair first."

        root_key_pair_id, root_private_enc, root_alg = root_kp_row
        root_alg = (root_alg or "RSA").upper()
        if root_alg != "RSA":
            root_alg = "RSA"

        # Atomically mark request as processing + reviewed
        cursor.execute(
            """
            UPDATE certificate_requests
            SET request_status = 'processing',
                reviewed_at = SYSDATETIME(),
                reviewed_by_admin_id = ?,
                review_note = ?
            OUTPUT INSERTED.user_id, INSERTED.key_pair_id, INSERTED.domain_name, INSERTED.csr_pem
            WHERE id = ?
              AND request_status = 'pending'
              AND request_type = 'issue'
            """,
            (
                int(admin_id),
                note,
                int(request_id),
            ),
        )

        req_row = cursor.fetchone()
        if not req_row:
            cursor.execute(
                """
                SELECT request_status
                FROM certificate_requests
                WHERE id = ?
                """,
                (int(request_id),),
            )
            existing = cursor.fetchone()
            if not existing:
                return False, "Request not found."
            return False, f"Request has already been processed (status: {existing[0]})."

        user_id, key_pair_id, domain_name, csr_pem = req_row
        domain_name = (domain_name or "").strip()
        if not domain_name:
            raise ValueError("Domain name is missing in request.")

        # Load user's public key and ensure the key pair matches the request
        cursor.execute(
            """
            SELECT owner_user_id, public_key
            FROM key_pairs
            WHERE id = ?
              AND owner_type = ?
            """,
            (int(key_pair_id), "customer"),
        )
        kp_row = cursor.fetchone()
        if not kp_row:
            raise ValueError("Key pair not found for this request.")

        owner_user_id, public_pem_str = kp_row
        if owner_user_id is None or int(owner_user_id) != int(user_id):
            raise ValueError("Invalid key pair for this request.")

        public_pem_bytes = (public_pem_str or "").encode("utf-8")
        try:
            user_public_key = serialization.load_pem_public_key(public_pem_bytes)
        except Exception as exc:
            raise ValueError("Cannot load user public key.") from exc

        # If CSR exists, validate it and use SAN DNS names from CSR.
        # If CSR is missing (legacy requests), continue using domain_name + selected keypair.
        csr_dns_names: List[str] = []
        csr_subject_country: Optional[str] = None
        csr_subject_org: Optional[str] = None
        csr_text = (csr_pem or "").strip()
        if csr_text:
            try:
                csr_obj = x509.load_pem_x509_csr(csr_text.encode("utf-8"))
            except Exception as exc:
                raise ValueError("Invalid CSR.") from exc

            try:
                c_attrs = csr_obj.subject.get_attributes_for_oid(NameOID.COUNTRY_NAME)
                if c_attrs:
                    v = (c_attrs[0].value or "").strip().upper()
                    if len(v) == 2 and v.isalpha():
                        csr_subject_country = v
            except Exception:
                csr_subject_country = None

            try:
                o_attrs = csr_obj.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
                if o_attrs:
                    v = (o_attrs[0].value or "").strip()
                    csr_subject_org = v or None
            except Exception:
                csr_subject_org = None

            try:
                is_valid_sig = getattr(csr_obj, "is_signature_valid", None)
                if is_valid_sig is False:
                    raise ValueError("Invalid CSR signature.")
            except Exception:
                pass

            try:
                csr_pub_der = csr_obj.public_key().public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                kp_pub_der = user_public_key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                if csr_pub_der != kp_pub_der:
                    raise ValueError("CSR public key does not match selected key pair.")
            except Exception as exc:
                raise ValueError("Cannot verify CSR public key.") from exc

            try:
                san_ext = csr_obj.extensions.get_extension_for_class(x509.SubjectAlternativeName)
                csr_dns_names = [
                    str(x).strip()
                    for x in san_ext.value.get_values_for_type(x509.DNSName)
                    if str(x).strip()
                ]
            except Exception:
                csr_dns_names = []

        # Load Root CA private key
        private_pem = _decrypt_private_key_pem(root_private_enc)
        try:
            root_private_key = load_pem_private_key(private_pem, password=None)
        except Exception as exc:
            raise ValueError("Cannot load Root CA private key from database.") from exc

        hash_algo = _get_hash_algorithm(settings)
        now = datetime.utcnow()
        validity_days = settings.get("default_validity_days") or 365
        not_before = now
        not_after = now + timedelta(days=int(validity_days))

        serial_number = x509.random_serial_number()

        subject_attrs = []
        if csr_subject_country:
            subject_attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, csr_subject_country))
        if csr_subject_org:
            subject_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, csr_subject_org))
        subject_attrs.append(x509.NameAttribute(NameOID.COMMON_NAME, domain_name))
        subject = x509.Name(subject_attrs)
        issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Good Web"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Good Web Root CA"),
            ]
        )

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(user_public_key)
            .serial_number(serial_number)
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName(x) for x in (csr_dns_names or [domain_name])]
                ),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
        )

        certificate = builder.sign(private_key=root_private_key, algorithm=hash_algo)

        public_key_der = certificate.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        certificate_pem = certificate.public_bytes(encoding=serialization.Encoding.PEM).decode("utf-8")

        subject_dn = f"CN={domain_name}"
        if csr_subject_org:
            subject_dn += f", O={csr_subject_org}"
        if csr_subject_country:
            subject_dn += f", C={csr_subject_country}"
        issuer_dn = "CN=Good Web Root CA, O=Good Web, C=VN"
        signature_algorithm_name = f"{hash_algo.name.upper()}with{root_alg}"

        cursor.execute(
            """
            INSERT INTO certificates (
                version,
                serial_number,
                subject_dn,
                issuer_dn,
                issuer_certificate_id,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,
                str(serial_number),
                subject_dn,
                issuer_dn,
                int(root_cert_id),
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
            raise ValueError("Failed to insert certificate into database.")

        certificate_id = int(new_cert_row[0])

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
                int(certificate_id),
                "issued",
                int(admin_id),
                None,
                None,
            ),
        )

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
                int(certificate_id),
                int(user_id),
                int(key_pair_id),
                int(request_id),
            ),
        )

        cursor.execute(
            """
            UPDATE certificate_requests
            SET certificate_id = ?,
                request_status = 'completed'
            WHERE id = ?
            """,
            (
                int(certificate_id),
                int(request_id),
            ),
        )

        conn.commit()

        return True, {
            "request_id": int(request_id),
            "status": "completed",
            "certificate_id": int(certificate_id),
            "key_pair_id": int(key_pair_id),
            "root_key_pair_id": int(root_key_pair_id),
        }

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error approving request: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def reject_certificate_request(
    request_id: int,
    admin_id: int,
    review_note: Optional[str] = None,
) -> Tuple[bool, object]:
    return _review_request(request_id, admin_id, "rejected", review_note=review_note)


def create_revoke_certificate_request(
    user_id: int,
    certificate_id: int,
    reason: Optional[str] = None,
) -> Tuple[bool, object]:
    """Create a revocation request for a certificate owned by the user."""

    note = (reason or "").strip() or None

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()

        # Ensure certificate belongs to this user and fetch key_pair_id + subject_dn
        cursor.execute(
            """
            SELECT TOP 1
                co.key_pair_id,
                c.subject_dn
            FROM certificate_ownership co
            INNER JOIN certificates c ON c.id = co.certificate_id
            WHERE co.user_id = ?
              AND co.certificate_id = ?
            ORDER BY co.id DESC
            """,
            (int(user_id), int(certificate_id)),
        )
        row = cursor.fetchone()
        if not row:
            return False, "Certificate not found or not owned by user."

        key_pair_id, subject_dn = row

        # Block if already revoked
        cursor.execute(
            """
            SELECT TOP 1 status
            FROM certificate_status
            WHERE certificate_id = ?
            ORDER BY changed_at DESC, id DESC
            """,
            (int(certificate_id),),
        )
        status_row = cursor.fetchone()
        current_status = (status_row[0] if status_row else None) or ""
        current_status_lc = str(current_status).lower()
        if current_status_lc == "revoked":
            return False, "Certificate has already been revoked."
        if current_status_lc and current_status_lc != "issued":
            return False, f"Certificate is not in 'issued' status (current: {current_status})."

        # Block duplicate pending/processing revocation requests
        cursor.execute(
            """
            SELECT TOP 1 id
            FROM certificate_requests
            WHERE certificate_id = ?
              AND request_type = 'revoke'
              AND request_status IN ('pending', 'processing')
            ORDER BY id DESC
            """,
            (int(certificate_id),),
        )
        if cursor.fetchone():
            return False, "A revocation request is already pending for this certificate."

        # Derive a domain-ish label from subject_dn if possible (CN=...)
        domain_name = None
        try:
            subj = str(subject_dn or "")
            parts = [p.strip() for p in subj.split(",")]
            for p in parts:
                if p.upper().startswith("CN="):
                    domain_name = p[3:].strip() or None
                    break
        except Exception:
            domain_name = None

        cursor.execute(
            """
            INSERT INTO certificate_requests (
                user_id,
                certificate_id,
                key_pair_id,
                request_type,
                request_status,
                csr_pem,
                domain_name,
                reason
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, 'revoke', 'pending', NULL, ?, ?)
            """,
            (
                int(user_id),
                int(certificate_id),
                int(key_pair_id) if key_pair_id is not None else None,
                domain_name,
                note,
            ),
        )

        new_row = cursor.fetchone()
        conn.commit()

        new_id = new_row[0] if new_row else None
        if new_id is None:
            return False, "Failed to create request."

        return True, {"request_id": int(new_id)}

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error creating revocation request: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def approve_revoke_certificate_request(
    request_id: int,
    admin_id: int,
    review_note: Optional[str] = None,
    revocation_reason_code: Optional[str] = None,
) -> Tuple[bool, object]:
    """Approve a revocation request and mark the certificate as revoked."""

    note = (review_note or "").strip() or None
    reason_code = (revocation_reason_code or "").strip() or None

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE certificate_requests
            SET request_status = 'processing',
                reviewed_at = SYSDATETIME(),
                reviewed_by_admin_id = ?,
                review_note = ?
            OUTPUT INSERTED.user_id, INSERTED.certificate_id, INSERTED.reason
            WHERE id = ?
              AND request_status = 'pending'
              AND request_type = 'revoke'
            """,
            (int(admin_id), note, int(request_id)),
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                """
                SELECT request_status
                FROM certificate_requests
                WHERE id = ?
                """,
                (int(request_id),),
            )
            existing = cursor.fetchone()
            if not existing:
                return False, "Request not found."
            return False, f"Request has already been processed (status: {existing[0]})."

        user_id, certificate_id, req_reason = row
        if certificate_id is None:
            raise ValueError("Certificate ID missing in revoke request.")

        # Ensure certificate belongs to the requesting user
        cursor.execute(
            """
            SELECT TOP 1 id
            FROM certificate_ownership
            WHERE certificate_id = ?
              AND user_id = ?
            """,
            (int(certificate_id), int(user_id)),
        )
        if not cursor.fetchone():
            raise ValueError("Certificate ownership does not match the request user.")

        # Ensure not already revoked
        cursor.execute(
            """
            SELECT TOP 1 status
            FROM certificate_status
            WHERE certificate_id = ?
            ORDER BY changed_at DESC, id DESC
            """,
            (int(certificate_id),),
        )
        st = cursor.fetchone()
        current_status = (st[0] if st else None) or ""
        if str(current_status).lower() == "revoked":
            raise ValueError("Certificate is already revoked.")

        final_reason = reason_code
        if not final_reason:
            final_reason = (str(req_reason or "").strip() or "user_request")
        final_reason = final_reason[:50]

        cursor.execute(
            """
            INSERT INTO certificate_status (
                certificate_id,
                status,
                changed_by_admin_id,
                revocation_reason_code,
                crl_id
            )
            VALUES (?, 'revoked', ?, ?, NULL)
            """,
            (int(certificate_id), int(admin_id), final_reason),
        )

        cursor.execute(
            """
            UPDATE certificate_requests
            SET request_status = 'completed'
            WHERE id = ?
            """,
            (int(request_id),),
        )

        conn.commit()
        return True, {
            "request_id": int(request_id),
            "status": "completed",
            "certificate_id": int(certificate_id),
            "user_id": int(user_id) if user_id is not None else None,
        }

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error approving revocation request: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def list_revoked_certificates_system() -> Tuple[bool, List[Dict]]:
    """List revoked certificates (system-wide), for both admin and user to view."""

    conn = get_db_connection()
    if not conn:
        return False, []

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                c.id AS certificate_id,
                c.serial_number,
                c.subject_dn,
                c.issuer_dn,
                s.changed_at AS revoked_at,
                s.changed_by_admin_id,
                s.revocation_reason_code
            FROM certificates c
            OUTER APPLY (
                SELECT TOP 1
                    status,
                    changed_at,
                    changed_by_admin_id,
                    revocation_reason_code
                FROM certificate_status cs
                WHERE cs.certificate_id = c.id
                ORDER BY cs.changed_at DESC, cs.id DESC
            ) s
            WHERE s.status = 'revoked'
            ORDER BY s.changed_at DESC, c.id DESC
            """
        )
        rows = cursor.fetchall() or []
        columns = [col[0] for col in cursor.description]
        data: List[Dict] = []
        for row in rows:
            item = dict(zip(columns, row))
            for k, v in list(item.items()):
                if isinstance(v, datetime):
                    item[k] = v.isoformat(sep=" ", timespec="seconds")
            data.append(item)
        return True, data

    except Exception:
        return False, []

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def list_issued_certificates_for_admin(limit: int = 20) -> Tuple[bool, List[Dict]]:
    """List currently-issued certificates across the whole system (admin view)."""

    limit = int(limit or 20)
    if limit <= 0:
        limit = 20
    if limit > 200:
        limit = 200

    conn = get_db_connection()
    if not conn:
        return False, []

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TOP (?)
                c.id AS certificate_id,
                c.serial_number,
                c.subject_dn,
                c.issuer_dn,
                c.valid_from,
                c.valid_to,
                u.username,
                co.user_id,
                co.key_pair_id,
                r.domain_name,
                s.status
            FROM certificate_ownership co
            INNER JOIN certificates c ON c.id = co.certificate_id
            INNER JOIN users u ON u.id = co.user_id
            LEFT JOIN certificate_requests r ON r.id = co.request_id
            OUTER APPLY (
                SELECT TOP 1 status
                FROM certificate_status cs
                WHERE cs.certificate_id = c.id
                ORDER BY cs.changed_at DESC, cs.id DESC
            ) s
            WHERE s.status = 'issued'
            ORDER BY c.id DESC
            """,
            (limit,),
        )

        rows = cursor.fetchall() or []
        columns = [col[0] for col in cursor.description]
        data: List[Dict] = []

        for row in rows:
            item = dict(zip(columns, row))
            for k, v in list(item.items()):
                if isinstance(v, datetime):
                    item[k] = v.isoformat(sep=" ", timespec="seconds")
            # Fallback domain from subject DN if request domain missing
            if not item.get("domain_name") and item.get("subject_dn"):
                try:
                    subj = str(item.get("subject_dn") or "")
                    parts = [p.strip() for p in subj.split(",")]
                    for p in parts:
                        if p.upper().startswith("CN="):
                            item["domain_name"] = p[3:].strip()
                            break
                except Exception:
                    pass
            data.append(item)

        return True, data

    except Exception:
        return False, []

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def admin_revoke_certificate(
    certificate_id: int,
    admin_id: int,
    revocation_reason_code: Optional[str] = None,
) -> Tuple[bool, object]:
    """Directly revoke a certificate (admin action)."""

    reason_code = (revocation_reason_code or "").strip() or "admin_revoke"
    reason_code = reason_code[:50]

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT TOP 1 id
            FROM certificates
            WHERE id = ?
            """,
            (int(certificate_id),),
        )
        if not cursor.fetchone():
            return False, "Certificate not found."

        cursor.execute(
            """
            SELECT TOP 1 status
            FROM certificate_status
            WHERE certificate_id = ?
            ORDER BY changed_at DESC, id DESC
            """,
            (int(certificate_id),),
        )
        st = cursor.fetchone()
        current_status = (st[0] if st else None) or ""
        if str(current_status).lower() == "revoked":
            return False, "Certificate has already been revoked."

        cursor.execute(
            """
            INSERT INTO certificate_status (
                certificate_id,
                status,
                changed_by_admin_id,
                revocation_reason_code,
                crl_id
            )
            VALUES (?, 'revoked', ?, ?, NULL)
            """,
            (int(certificate_id), int(admin_id), reason_code),
        )

        conn.commit()
        return True, {"certificate_id": int(certificate_id), "status": "revoked"}

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error revoking certificate: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def admin_renew_certificate(
    certificate_id: int,
    admin_id: int,
) -> Tuple[bool, object]:
    """Renew a certificate by issuing a new certificate with same key pair and CN.

    Creates a new certificate record + status 'issued' + ownership mapping.
    """

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()

        settings = _load_system_settings(cursor)
        if not settings:
            return False, "System settings not configured for certificate generation."

        # Ensure Root CA certificate exists
        cursor.execute(
            """
            SELECT TOP 1 c.id, c.certificate_pem
            FROM certificates c
            INNER JOIN certificate_ownership co ON co.certificate_id = c.id
            INNER JOIN key_pairs kp ON kp.id = co.key_pair_id
            INNER JOIN certificate_status cs ON cs.certificate_id = c.id
            WHERE kp.owner_type = ?
              AND cs.status = 'issued'
            ORDER BY c.id DESC
            """,
            ("root_ca",),
        )
        root_cert_row = cursor.fetchone()
        if not root_cert_row:
            return False, "Root CA certificate not found. Please create Root CA certificate first."
        root_cert_id, _root_cert_pem = root_cert_row

        # Load active Root CA key pair (must have private key for signing)
        cursor.execute(
            """
            SELECT TOP 1 id, private_key_encrypted, algorithm
            FROM key_pairs
            WHERE owner_type = ?
              AND status = 'active'
            ORDER BY id DESC
            """,
            ("root_ca",),
        )
        root_kp_row = cursor.fetchone()
        if not root_kp_row:
            return False, "No active Root CA key pair found. Please generate Root CA key pair first."

        root_key_pair_id, root_private_enc, root_alg = root_kp_row
        root_alg = (root_alg or "RSA").upper()
        if root_alg != "RSA":
            root_alg = "RSA"

        # Load certificate + ownership
        cursor.execute(
            """
            SELECT TOP 1
                c.subject_dn,
                co.user_id,
                co.key_pair_id
            FROM certificates c
            INNER JOIN certificate_ownership co ON co.certificate_id = c.id
            WHERE c.id = ?
            ORDER BY co.id DESC
            """,
            (int(certificate_id),),
        )
        cert_row = cursor.fetchone()
        if not cert_row:
            return False, "Certificate not found."

        subject_dn, user_id, key_pair_id = cert_row
        if user_id is None or key_pair_id is None:
            return False, "Certificate ownership data missing."

        # Only renew if current status is issued
        cursor.execute(
            """
            SELECT TOP 1 status
            FROM certificate_status
            WHERE certificate_id = ?
            ORDER BY changed_at DESC, id DESC
            """,
            (int(certificate_id),),
        )
        st = cursor.fetchone()
        current_status = (st[0] if st else None) or ""
        if str(current_status).lower() != "issued":
            return False, f"Certificate is not in 'issued' status (current: {current_status})."

        # Get user's public key (from key pair)
        cursor.execute(
            """
            SELECT public_key
            FROM key_pairs
            WHERE id = ?
              AND owner_type = ?
            """,
            (int(key_pair_id), "customer"),
        )
        kp_row = cursor.fetchone()
        if not kp_row or not kp_row[0]:
            return False, "Key pair not found for renewal."

        public_pem_bytes = str(kp_row[0]).encode("utf-8")
        try:
            user_public_key = serialization.load_pem_public_key(public_pem_bytes)
        except Exception as exc:
            return False, f"Cannot load user public key: {exc}"

        # Parse CN/O/C from subject_dn to preserve subject identity
        domain_name = None
        subject_org = None
        subject_country = None
        try:
            subj = str(subject_dn or "")
            parts = [p.strip() for p in subj.split(",")]
            for p in parts:
                if p.upper().startswith("CN="):
                    domain_name = p[3:].strip() or None
                elif p.upper().startswith("O="):
                    subject_org = p.split("=", 1)[1].strip() or None
                elif p.upper().startswith("C="):
                    cc = p.split("=", 1)[1].strip().upper() if "=" in p else ""
                    if len(cc) == 2 and cc.isalpha():
                        subject_country = cc
        except Exception:
            domain_name = None

        if not domain_name:
            return False, "Cannot determine domain (CN) from existing certificate."

        # Load Root CA private key
        private_pem = _decrypt_private_key_pem(root_private_enc)
        try:
            root_private_key = load_pem_private_key(private_pem, password=None)
        except Exception as exc:
            return False, f"Cannot load Root CA private key from database: {exc}"

        hash_algo = _get_hash_algorithm(settings)
        now = datetime.utcnow()
        validity_days = settings.get("default_validity_days") or 365
        not_before = now
        not_after = now + timedelta(days=int(validity_days))
        serial_number = x509.random_serial_number()

        subject_attrs = []
        if subject_country:
            subject_attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, subject_country))
        if subject_org:
            subject_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, subject_org))
        subject_attrs.append(x509.NameAttribute(NameOID.COMMON_NAME, domain_name))
        subject = x509.Name(subject_attrs)
        issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Good Web"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Good Web Root CA"),
            ]
        )

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(user_public_key)
            .serial_number(serial_number)
            .not_valid_before(not_before)
            .not_valid_after(not_after)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(domain_name)]),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
        )

        certificate = builder.sign(private_key=root_private_key, algorithm=hash_algo)
        public_key_der = certificate.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        certificate_pem = certificate.public_bytes(encoding=serialization.Encoding.PEM).decode("utf-8")

        subject_dn_new = f"CN={domain_name}"
        if subject_org:
            subject_dn_new += f", O={subject_org}"
        if subject_country:
            subject_dn_new += f", C={subject_country}"
        issuer_dn = "CN=Good Web Root CA, O=Good Web, C=VN"
        signature_algorithm_name = f"{hash_algo.name.upper()}with{root_alg}"

        cursor.execute(
            """
            INSERT INTO certificates (
                version,
                serial_number,
                subject_dn,
                issuer_dn,
                issuer_certificate_id,
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,
                str(serial_number),
                subject_dn_new,
                issuer_dn,
                int(root_cert_id),
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
            return False, "Failed to insert renewed certificate."
        new_certificate_id = int(new_cert_row[0])

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
            (int(new_certificate_id), "issued", int(admin_id), None, None),
        )

        cursor.execute(
            """
            INSERT INTO certificate_ownership (
                certificate_id,
                user_id,
                key_pair_id,
                request_id
            )
            VALUES (?, ?, ?, NULL)
            """,
            (int(new_certificate_id), int(user_id), int(key_pair_id)),
        )

        conn.commit()
        return True, {
            "old_certificate_id": int(certificate_id),
            "new_certificate_id": int(new_certificate_id),
            "domain_name": domain_name,
            "key_pair_id": int(key_pair_id),
            "root_key_pair_id": int(root_key_pair_id),
        }

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error renewing certificate: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def list_certificates_for_user(user_id: int) -> Tuple[bool, List[Dict]]:
    """List certificates that belong to a user (customer)."""

    conn = get_db_connection()
    if not conn:
        return False, []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                c.id AS certificate_id,
                co.key_pair_id,
                co.request_id,
                r.domain_name,
                s.status,
                c.valid_from,
                c.valid_to
            FROM certificate_ownership co
            INNER JOIN certificates c ON c.id = co.certificate_id
            LEFT JOIN certificate_requests r ON r.id = co.request_id
            OUTER APPLY (
                SELECT TOP 1 status
                FROM certificate_status cs
                WHERE cs.certificate_id = c.id
                ORDER BY cs.changed_at DESC, cs.id DESC
            ) s
            WHERE co.user_id = ?
            ORDER BY c.id DESC
            """,
            (int(user_id),),
        )

        rows = cursor.fetchall() or []
        columns = [col[0] for col in cursor.description]
        data: List[Dict] = []

        for row in rows:
            item = dict(zip(columns, row))
            # Make JSON-serializable
            for k, v in list(item.items()):
                if isinstance(v, datetime):
                    item[k] = v.isoformat(sep=" ", timespec="seconds")
            data.append(item)

        return True, data

    except Exception:
        return False, []

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()


def get_user_certificate_pem(user_id: int, certificate_id: int) -> Tuple[bool, object]:
    """Return PEM for a certificate owned by a user."""

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.certificate_pem
            FROM certificates c
            INNER JOIN certificate_ownership co ON co.certificate_id = c.id
            WHERE c.id = ?
              AND co.user_id = ?
            """,
            (int(certificate_id), int(user_id)),
        )

        row = cursor.fetchone()
        if not row or not row[0]:
            return False, "Certificate not found."

        return True, row[0]

    except Exception as exc:
        return False, f"Error loading certificate: {exc}"

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()
