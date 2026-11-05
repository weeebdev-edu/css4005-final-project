-- EXAMPLE least-privilege users for MySQL 8.4. Adapt it; don't run it blindly.
-- Run as root. Replace the placeholder passwords with values from your
-- secret manager (never commit real ones).

-- Server-side password policy (component shipped with MySQL 8.x):
INSTALL COMPONENT 'file://component_validate_password';
SET GLOBAL validate_password.length = 12;
SET GLOBAL validate_password.policy = 'MEDIUM';   -- upper/lower/digit/special

CREATE DATABASE IF NOT EXISTS campus;

CREATE USER 'admin'@'%'  IDENTIFIED BY 'CHANGE-ME-admin-Pw1!';
CREATE USER 'app_rw'@'%' IDENTIFIED BY 'CHANGE-ME-rw-Passw0rd!' WITH MAX_USER_CONNECTIONS 50;
CREATE USER 'app_ro'@'%' IDENTIFIED BY 'CHANGE-ME-ro-Passw0rd!' WITH MAX_USER_CONNECTIONS 10;

GRANT ALL PRIVILEGES ON campus.* TO 'admin'@'%';
-- CREATE/ALTER/INDEX because the app creates its tables on startup;
-- drop them once tables are managed by migrations run as admin.
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON campus.* TO 'app_rw'@'%';
GRANT SELECT ON campus.* TO 'app_ro'@'%';

-- Tighter: replace '%' with the app subnet, e.g. 'app_rw'@'10.42.2.%'.
FLUSH PRIVILEGES;
