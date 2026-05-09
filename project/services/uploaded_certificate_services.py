from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID

from db import get_db_connection


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_x509_certificate(cert_bytes: bytes) -> x509.Certificate:
    data = cert_bytes.strip()
    # Heuristic: PEM has BEGIN marker
    if b"-----BEGIN" in data[:200] and b"CERTIFICATE" in data[:400]:
        begin = b"-----BEGIN CERTIFICATE-----"
        end = b"-----END CERTIFICATE-----"
        if begin in data:
            start = data.find(begin)
            stop = data.find(end, start)
            if stop != -1:
                block = data[start : stop + len(end)]
                return x509.load_pem_x509_certificate(block)
        return x509.load_pem_x509_certificate(data)
    return x509.load_der_x509_certificate(data)


def _extract_subject_fields(cert: x509.Certificate) -> Dict[str, Optional[str]]:
    def first_value(oid: NameOID) -> Optional[str]:
        try:
            attrs = cert.subject.get_attributes_for_oid(oid)
            if not attrs:
                return None
            return str(attrs[0].value).strip() or None
        except Exception:
            return None

    return {
        "subject_cn": first_value(NameOID.COMMON_NAME),
        "subject_o": first_value(NameOID.ORGANIZATION_NAME),
    }


def _format_dt(dt: datetime) -> str:
    dt = _to_utc(dt)
    # Keep simple: 'YYYY-MM-DD HH:MM:SSZ'
    return dt.strftime("%Y-%m-%d %H:%M:%SZ")


def parse_certificate_for_tracking(
    certificate_bytes: bytes,
) -> Tuple[bool, object]:
    """Parse a certificate (PEM/DER) to fields suitable for tracking."""

    if not certificate_bytes:
        return False, "Certificate file is empty."

    try:
        cert = _load_x509_certificate(certificate_bytes)
    except Exception as exc:
        return False, f"Invalid certificate format: {exc}"

    # Normalize to PEM for storage
    try:
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    except Exception:
        cert_pem = certificate_bytes.decode("utf-8", errors="ignore")

    subject_dn = cert.subject.rfc4514_string()
    issuer_dn = cert.issuer.rfc4514_string()

    try:
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
    except Exception:
        # Fallback for older cryptography versions
        not_before = cert.not_valid_before
        not_after = cert.not_valid_after

    fp = cert.fingerprint(hashes.SHA256()).hex()

    subject_fields = _extract_subject_fields(cert)

    return (
        True,
        {
            "certificate_pem": cert_pem,
            "subject_dn": subject_dn,
            "issuer_dn": issuer_dn,
            "serial_number": str(cert.serial_number),
            "valid_from": _to_utc(not_before),
            "valid_to": _to_utc(not_after),
            "fingerprint_sha256": fp,
            **subject_fields,
        },
    )


def upload_certificate_for_user_tracking(
    user_id: int,
    file_name: str,
    certificate_bytes: bytes,
) -> Tuple[bool, object]:
    """Store an uploaded external certificate for the given user."""

    file_name = (file_name or "certificate.pem").strip() or "certificate.pem"
    if len(file_name) > 255:
        file_name = file_name[:255]

    ok, parsed = parse_certificate_for_tracking(certificate_bytes)
    if not ok:
        return False, parsed

    data: Dict = parsed  # type: ignore[assignment]

    conn = get_db_connection()
    if not conn:
        return False, "cannot connect to database"

    cursor = None
    try:
        cursor = conn.cursor()

        # De-dupe per user by fingerprint
        cursor.execute(
            """
            SELECT TOP 1 id
            FROM uploaded_certificates
            WHERE user_id = ?
              AND fingerprint_sha256 = ?
            ORDER BY id DESC
            """,
            (int(user_id), str(data["fingerprint_sha256"])),
        )
        existing = cursor.fetchone()
        if existing:
            return True, {
                "uploaded_certificate_id": int(existing[0]),
                "message": "Certificate already tracked.",
                "fingerprint_sha256": data["fingerprint_sha256"],
            }

        cursor.execute(
            """
            INSERT INTO uploaded_certificates (
                user_id,
                file_name,
                certificate_pem,
                subject_dn,
                issuer_dn,
                serial_number,
                valid_from,
                valid_to,
                fingerprint_sha256
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                file_name,
                str(data["certificate_pem"]),
                str(data["subject_dn"]),
                str(data["issuer_dn"]),
                str(data["serial_number"]),
                data["valid_from"],
                data["valid_to"],
                str(data["fingerprint_sha256"]),
            ),
        )
        row = cursor.fetchone()
        conn.commit()

        new_id = int(row[0]) if row else None
        return True, {
            "uploaded_certificate_id": new_id,
            "fingerprint_sha256": data["fingerprint_sha256"],
            "subject_cn": data.get("subject_cn"),
            "subject_o": data.get("subject_o"),
        }

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, f"Error uploading certificate: {exc}"

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def list_uploaded_certificates_for_user(user_id: int, limit: int = 50) -> Tuple[bool, List[Dict]]:
    limit = int(limit or 50)
    if limit <= 0:
        limit = 50
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
                id,
                file_name,
                subject_dn,
                issuer_dn,
                serial_number,
                valid_from,
                valid_to,
                fingerprint_sha256,
                uploaded_at
            FROM uploaded_certificates
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (limit, int(user_id)),
        )

        rows = cursor.fetchall() or []
        cols = [c[0] for c in cursor.description]

        now = _now_utc()
        items: List[Dict] = []
        for r in rows:
            item = dict(zip(cols, r))

            valid_from = item.get("valid_from")
            valid_to = item.get("valid_to")
            try:
                vf = _to_utc(valid_from) if isinstance(valid_from, datetime) else None
                vt = _to_utc(valid_to) if isinstance(valid_to, datetime) else None
            except Exception:
                vf = None
                vt = None

            if vf and now < vf:
                status = "not_yet_valid"
            elif vt and now > vt:
                status = "expired"
            else:
                status = "valid"

            remaining_days = None
            if vt:
                remaining_days = int((vt - now).total_seconds() // 86400)

            # Extract CN/O from subject_dn (quick parse; OK for display)
            subject_dn = str(item.get("subject_dn") or "")
            cn = None
            org = None
            try:
                parts = [p.strip() for p in subject_dn.split(",")]
                for p in parts:
                    if p.upper().startswith("CN=") and not cn:
                        cn = p[3:].strip() or None
                    elif (p.upper().startswith("O=") or p.upper().startswith("O ")) and not org:
                        org = p.split("=", 1)[1].strip() if "=" in p else None
            except Exception:
                cn = None
                org = None

            # Format datetimes for templates/JSON
            if isinstance(item.get("valid_from"), datetime):
                item["valid_from"] = _format_dt(item["valid_from"])
            if isinstance(item.get("valid_to"), datetime):
                item["valid_to"] = _format_dt(item["valid_to"])
            if isinstance(item.get("uploaded_at"), datetime):
                item["uploaded_at"] = _format_dt(item["uploaded_at"])

            item["domain_name"] = cn
            item["owner_name"] = org
            item["status"] = status
            item["remaining_days"] = remaining_days

            items.append(item)

        return True, items

    except Exception:
        return False, []

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()
