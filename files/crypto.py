"""
crypto.py
Tất cả logic liên quan đến X.509: tạo key pair, tạo Root CA, ký CSR.
Sử dụng thư viện `cryptography` của Python (pip install cryptography).
"""

import datetime
import ipaddress
import random

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


# ── Hằng số ───────────────────────────────────────────────────────────────────
KEY_SIZE        = 2048          # RSA key size
PUBLIC_EXPONENT = 65537
DEFAULT_VALIDITY_DAYS = 365     # chứng chỉ thường: 1 năm
ROOT_VALIDITY_DAYS    = 3650    # Root CA: 10 năm


# ── 1. Tạo cặp khóa RSA ───────────────────────────────────────────────────────
def generate_key_pair() -> rsa.RSAPrivateKey:
    """Sinh cặp khóa RSA 2048-bit."""
    return rsa.generate_private_key(
        public_exponent=PUBLIC_EXPONENT,
        key_size=KEY_SIZE,
        backend=default_backend()
    )


def private_key_to_pem(private_key: rsa.RSAPrivateKey, password: bytes = None) -> str:
    """Xuất private key ra PEM string (tùy chọn mã hóa bằng password)."""
    encryption = (
        serialization.BestAvailableEncryption(password)
        if password
        else serialization.NoEncryption()
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=encryption
    ).decode("utf-8")


def public_key_to_pem(private_key: rsa.RSAPrivateKey) -> str:
    """Xuất public key ra PEM string."""
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")


def load_private_key_from_pem(pem_str: str, password: bytes = None) -> rsa.RSAPrivateKey:
    return serialization.load_pem_private_key(
        pem_str.encode("utf-8"),
        password=password,
        backend=default_backend()
    )


def load_cert_from_pem(pem_str: str) -> x509.Certificate:
    return x509.load_pem_x509_certificate(
        pem_str.encode("utf-8"),
        default_backend()
    )


# ── 2. Tạo Root CA (self-signed) ──────────────────────────────────────────────
def create_root_ca(
    common_name: str,
    organization: str = "X509 CA System",
    country: str = "VN",
    validity_days: int = ROOT_VALIDITY_DAYS
) -> dict:
    """
    Tạo Root Certificate Authority (level 0).
    Trả về dict: {cert_pem, private_key_pem, public_key_pem, serial_number}
    """
    private_key = generate_key_pair()
    public_key  = private_key.public_key()

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             country),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        organization),
        x509.NameAttribute(NameOID.COMMON_NAME,              common_name),
    ])

    serial = x509.random_serial_number()
    now    = datetime.datetime.utcnow()

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(serial)
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=validity_days))
        # Extensions bắt buộc cho CA
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False
            ),
            critical=True
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    return {
        "cert_pem":        cert_pem,
        "private_key_pem": private_key_to_pem(private_key),
        "public_key_pem":  public_key_to_pem(private_key),
        "serial_number":   str(serial),
        "not_before":      now,
        "not_after":       now + datetime.timedelta(days=validity_days),
    }


# ── 3. Tạo CSR (phía khách hàng) ─────────────────────────────────────────────
def create_csr(
    domain: str,
    organization: str = "",
    country: str = "VN"
) -> dict:
    """
    Sinh cặp khóa + CSR cho khách hàng.
    Trả về dict: {csr_pem, private_key_pem, public_key_pem}
    """
    private_key = generate_key_pair()

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME,      country),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization or domain),
            x509.NameAttribute(NameOID.COMMON_NAME,       domain),
        ]))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(domain)]),
            critical=False
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    return {
        "csr_pem":         csr_pem,
        "private_key_pem": private_key_to_pem(private_key),
        "public_key_pem":  public_key_to_pem(private_key),
    }


# ── 4. Ký CSR → cấp chứng nhận ───────────────────────────────────────────────
def sign_csr(
    csr_pem: str,
    ca_cert_pem: str,
    ca_private_key_pem: str,
    validity_days: int = DEFAULT_VALIDITY_DAYS
) -> dict:
    """
    Admin dùng Root CA để ký CSR → cấp X.509 certificate.
    Trả về dict: {cert_pem, serial_number, not_before, not_after}
    """
    csr            = x509.load_pem_x509_csr(csr_pem.encode(), default_backend())
    ca_cert        = load_cert_from_pem(ca_cert_pem)
    ca_private_key = load_private_key_from_pem(ca_private_key_pem)

    serial = x509.random_serial_number()
    now    = datetime.datetime.utcnow()

    cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(serial)
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=validity_days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=True,
                key_encipherment=True,  data_encipherment=False,
                key_agreement=False,    key_cert_sign=False,
                crl_sign=False,         encipher_only=False, decipher_only=False
            ),
            critical=True
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False
        )
        # Copy SAN từ CSR nếu có
        .add_extension(
            _get_san_from_csr(csr),
            critical=False
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_private_key.public_key()),
            critical=False
        )
        .sign(ca_private_key, hashes.SHA256(), default_backend())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    return {
        "cert_pem":      cert_pem,
        "serial_number": str(serial),
        "not_before":    now,
        "not_after":     now + datetime.timedelta(days=validity_days),
    }


def _get_san_from_csr(csr: x509.CertificateSigningRequest) -> x509.SubjectAlternativeName:
    """Lấy SAN từ CSR, nếu không có thì dùng CN làm DNSName."""
    try:
        return csr.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        cn_attr = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        cn = cn_attr[0].value if cn_attr else "unknown"
        return x509.SubjectAlternativeName([x509.DNSName(cn)])


# ── 5. Kiểm tra hiệu lực ─────────────────────────────────────────────────────
def cert_is_valid(cert_pem: str) -> bool:
    """Kiểm tra cert còn hạn không."""
    cert = load_cert_from_pem(cert_pem)
    now  = datetime.datetime.utcnow()
    return cert.not_valid_before <= now <= cert.not_valid_after


def cert_info(cert_pem: str) -> dict:
    """Trả về thông tin tóm tắt của cert."""
    cert = load_cert_from_pem(cert_pem)
    cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    return {
        "common_name":   cn_attrs[0].value if cn_attrs else "",
        "serial_number": str(cert.serial_number),
        "not_before":    cert.not_valid_before,
        "not_after":     cert.not_valid_after,
        "issuer":        cert.issuer.rfc4514_string(),
    }
