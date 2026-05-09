-- Debug queries for ea_db
USE ea_db;

-- Users and related entities
SELECT * FROM users;
SELECT * FROM key_pairs;
SELECT * FROM certificates;
SELECT * FROM certificate_ownership;
SELECT * FROM certificate_requests;
SELECT * FROM certificate_requests;
SELECT * FROM system_settings;
SELECT * FROM certificate_revocation_list;
SELECT * FROM uploaded_certificates;
SELECT * FROM activity_logs;
SELECT * FROM certificate_domains;
-- You can add WHERE clauses here while debugging, for example:
-- SELECT * FROM users WHERE username = 'testuser';
