-- SQL Server schema for ea_db
ALTER DATABASE ea_db SET MULTI_USER WITH ROLLBACK IMMEDIATE;
-- Tạo database nếu chưa có (không set SINGLE_USER để tránh khóa)
IF DB_ID('ea_db') IS NULL
BEGIN
	CREATE DATABASE ea_db;
END;
GO

USE ea_db;
GO

-- Xóa FOREIGN KEY cũ (nếu có) trước khi drop bảng
IF OBJECT_ID('fk_activity_logs_user', 'F') IS NOT NULL
	ALTER TABLE activity_logs DROP CONSTRAINT fk_activity_logs_user;

IF OBJECT_ID('fk_uploaded_certificates_user', 'F') IS NOT NULL
	ALTER TABLE uploaded_certificates DROP CONSTRAINT fk_uploaded_certificates_user;

IF OBJECT_ID('fk_crl_issuer_certificate', 'F') IS NOT NULL
	ALTER TABLE certificate_revocation_list DROP CONSTRAINT fk_crl_issuer_certificate;

IF OBJECT_ID('fk_crl_generated_by_admin', 'F') IS NOT NULL
	ALTER TABLE certificate_revocation_list DROP CONSTRAINT fk_crl_generated_by_admin;

IF OBJECT_ID('fk_certificate_requests_user', 'F') IS NOT NULL
	ALTER TABLE certificate_requests DROP CONSTRAINT fk_certificate_requests_user;

IF OBJECT_ID('fk_certificate_requests_certificate', 'F') IS NOT NULL
	ALTER TABLE certificate_requests DROP CONSTRAINT fk_certificate_requests_certificate;

IF OBJECT_ID('fk_certificate_requests_key_pair', 'F') IS NOT NULL
	ALTER TABLE certificate_requests DROP CONSTRAINT fk_certificate_requests_key_pair;

IF OBJECT_ID('fk_certificate_requests_reviewed_by_admin', 'F') IS NOT NULL
	ALTER TABLE certificate_requests DROP CONSTRAINT fk_certificate_requests_reviewed_by_admin;

IF OBJECT_ID('fk_certificates_user', 'F') IS NOT NULL
	ALTER TABLE certificates DROP CONSTRAINT fk_certificates_user;

IF OBJECT_ID('fk_certificates_key_pair', 'F') IS NOT NULL
	ALTER TABLE certificates DROP CONSTRAINT fk_certificates_key_pair;

IF OBJECT_ID('fk_certificates_request', 'F') IS NOT NULL
	ALTER TABLE certificates DROP CONSTRAINT fk_certificates_request;

IF OBJECT_ID('fk_certificates_revoked_by_admin', 'F') IS NOT NULL
	ALTER TABLE certificates DROP CONSTRAINT fk_certificates_revoked_by_admin;

IF OBJECT_ID('fk_certificates_crl', 'F') IS NOT NULL
	ALTER TABLE certificates DROP CONSTRAINT fk_certificates_crl;
GO

-- Xóa các bảng cũ nếu tồn tại (theo đúng thứ tự phụ thuộc FK)
IF OBJECT_ID('dbo.activity_logs', 'U') IS NOT NULL DROP TABLE dbo.activity_logs;
IF OBJECT_ID('dbo.uploaded_certificates', 'U') IS NOT NULL DROP TABLE dbo.uploaded_certificates;
IF OBJECT_ID('dbo.certificate_revocation_list', 'U') IS NOT NULL DROP TABLE dbo.certificate_revocation_list;
IF OBJECT_ID('dbo.system_settings', 'U') IS NOT NULL DROP TABLE dbo.system_settings;
IF OBJECT_ID('dbo.certificate_requests', 'U') IS NOT NULL DROP TABLE dbo.certificate_requests;
IF OBJECT_ID('dbo.certificates', 'U') IS NOT NULL DROP TABLE dbo.certificates;
IF OBJECT_ID('dbo.key_pairs', 'U') IS NOT NULL DROP TABLE dbo.key_pairs;
IF OBJECT_ID('dbo.users', 'U') IS NOT NULL DROP TABLE dbo.users;
GO

-- USERS: admin & customer accounts
CREATE TABLE users (
	id BIGINT IDENTITY(1,1) PRIMARY KEY,
	username NVARCHAR(100) NOT NULL UNIQUE,
	password_hash NVARCHAR(255) NOT NULL,
	role NVARCHAR(20) NOT NULL CHECK (role IN ('admin', 'customer')),
	email NVARCHAR(255) NOT NULL UNIQUE
);

-- KEY_PAIRS: key pairs for customers and Root CA
CREATE TABLE key_pairs (
	id BIGINT IDENTITY(1,1) PRIMARY KEY,
	owner_user_id BIGINT NULL,
	owner_type NVARCHAR(20) NOT NULL CHECK (owner_type IN ('admin', 'customer', 'root_ca', 'system')),
	public_key NVARCHAR(MAX) NOT NULL,
	private_key_encrypted NVARCHAR(MAX) NOT NULL,
	algorithm NVARCHAR(50) NOT NULL,
	key_size INT NOT NULL,
	purpose NVARCHAR(100) NOT NULL,
	status NVARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive', 'compromised', 'retired')) DEFAULT 'active'
);

-- CERTIFICATES: internal certificates issued by the system
CREATE TABLE certificates (
	version TINYINT NOT NULL DEFAULT 3,
	id BIGINT IDENTITY(1,1) PRIMARY KEY,
	user_id BIGINT NOT NULL,
	key_pair_id BIGINT NULL,
	request_id BIGINT NULL,
	serial_number NVARCHAR(100) NOT NULL UNIQUE,
	subject_dn NVARCHAR(MAX) NOT NULL,
	issuer_dn NVARCHAR(MAX) NOT NULL,
	valid_from DATETIME2 NOT NULL,
	valid_to DATETIME2 NOT NULL,
	issuer_unique_identifier NVARCHAR(255) NULL,
	subject_unique_identifier NVARCHAR(255) NULL,
	status NVARCHAR(30) NOT NULL CHECK (status IN ('pending', 'issued', 'revocation_requested', 'revoked', 'expired')),
	revoked_at DATETIME2 NULL,
	revoked_by_admin_id BIGINT NULL,
	revocation_reason_code NVARCHAR(50) NULL,
	crl_id BIGINT NULL,
	signature_value NVARCHAR(MAX) NOT NULL,
	signature_algorithm NVARCHAR(100) NOT NULL
);

-- CERTIFICATE_REQUESTS: issue / revoke / renew / reissue
CREATE TABLE certificate_requests (
	id BIGINT IDENTITY(1,1) PRIMARY KEY,
	user_id BIGINT NOT NULL,
	certificate_id BIGINT NULL,
	key_pair_id BIGINT NULL,
	request_type NVARCHAR(20) NOT NULL CHECK (request_type IN ('issue', 'revoke', 'renew', 'reissue')),
	request_status NVARCHAR(20) NOT NULL CHECK (request_status IN ('pending', 'approved', 'rejected', 'processing', 'completed', 'cancelled')) DEFAULT 'pending',
	csr_pem NVARCHAR(MAX) NULL,
	domain_name NVARCHAR(255) NULL,
	reason NVARCHAR(MAX) NULL,
	submitted_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
	reviewed_at DATETIME2 NULL,
	reviewed_by_admin_id BIGINT NULL,
	review_note NVARCHAR(MAX) NULL
);

-- SYSTEM_SETTINGS: global configuration
CREATE TABLE system_settings (
	id TINYINT NOT NULL PRIMARY KEY,
	default_key_algorithm NVARCHAR(50) NOT NULL,
	default_hash_algorithm NVARCHAR(50) NOT NULL,
	default_key_size INT NOT NULL,
	default_validity_days INT NOT NULL
);

-- CERTIFICATE_REVOCATION_LIST: each generated CRL
CREATE TABLE certificate_revocation_list (
	id BIGINT IDENTITY(1,1) PRIMARY KEY,
	crl_number BIGINT NOT NULL UNIQUE,
	issuer_certificate_id BIGINT NOT NULL,
	this_update DATETIME2 NOT NULL,
	next_update DATETIME2 NOT NULL,
	crl_pem NVARCHAR(MAX) NOT NULL,
	generated_by_admin_id BIGINT NOT NULL,
	generated_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);

-- UPLOADED_CERTIFICATES: external certificates uploaded for tracking
CREATE TABLE uploaded_certificates (
	id BIGINT IDENTITY(1,1) PRIMARY KEY,
	user_id BIGINT NOT NULL,
	file_name NVARCHAR(255) NOT NULL,
	certificate_pem NVARCHAR(MAX) NOT NULL,
	subject_dn NVARCHAR(MAX) NOT NULL,
	issuer_dn NVARCHAR(MAX) NOT NULL,
	serial_number NVARCHAR(100) NOT NULL,
	valid_from DATETIME2 NOT NULL,
	valid_to DATETIME2 NOT NULL,
	fingerprint_sha256 CHAR(64) NOT NULL,
	uploaded_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);

-- ACTIVITY_LOGS: main system activity log
CREATE TABLE activity_logs (
	id BIGINT IDENTITY(1,1) PRIMARY KEY,
	user_id BIGINT NULL,
	action_type NVARCHAR(50) NOT NULL,
	entity_type NVARCHAR(50) NOT NULL,
	entity_id BIGINT NULL,
	description NVARCHAR(MAX) NULL,
	created_at DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);

-- FOREIGN KEYS

ALTER TABLE key_pairs
	ADD CONSTRAINT fk_key_pairs_owner_user
		FOREIGN KEY (owner_user_id) REFERENCES users(id);

ALTER TABLE certificates
	ADD CONSTRAINT fk_certificates_user
		FOREIGN KEY (user_id) REFERENCES users(id);

ALTER TABLE certificates
	ADD CONSTRAINT fk_certificates_key_pair
		FOREIGN KEY (key_pair_id) REFERENCES key_pairs(id);

ALTER TABLE certificates
	ADD CONSTRAINT fk_certificates_request
		FOREIGN KEY (request_id) REFERENCES certificate_requests(id);

ALTER TABLE certificates
	ADD CONSTRAINT fk_certificates_revoked_by_admin
		FOREIGN KEY (revoked_by_admin_id) REFERENCES users(id);

ALTER TABLE certificates
	ADD CONSTRAINT fk_certificates_crl
		FOREIGN KEY (crl_id) REFERENCES certificate_revocation_list(id);

ALTER TABLE certificate_requests
	ADD CONSTRAINT fk_certificate_requests_user
		FOREIGN KEY (user_id) REFERENCES users(id);

ALTER TABLE certificate_requests
	ADD CONSTRAINT fk_certificate_requests_certificate
		FOREIGN KEY (certificate_id) REFERENCES certificates(id);

ALTER TABLE certificate_requests
	ADD CONSTRAINT fk_certificate_requests_key_pair
		FOREIGN KEY (key_pair_id) REFERENCES key_pairs(id);

ALTER TABLE certificate_requests
	ADD CONSTRAINT fk_certificate_requests_reviewed_by_admin
		FOREIGN KEY (reviewed_by_admin_id) REFERENCES users(id);

ALTER TABLE certificate_revocation_list
	ADD CONSTRAINT fk_crl_issuer_certificate
		FOREIGN KEY (issuer_certificate_id) REFERENCES certificates(id);

ALTER TABLE certificate_revocation_list
	ADD CONSTRAINT fk_crl_generated_by_admin
		FOREIGN KEY (generated_by_admin_id) REFERENCES users(id);

ALTER TABLE uploaded_certificates
	ADD CONSTRAINT fk_uploaded_certificates_user
		FOREIGN KEY (user_id) REFERENCES users(id);

ALTER TABLE activity_logs
	ADD CONSTRAINT fk_activity_logs_user
		FOREIGN KEY (user_id) REFERENCES users(id);
