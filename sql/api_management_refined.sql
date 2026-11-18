/*
===============================================================================
DBMS MINI PROJECT
Enterprise API Governance, Discovery and Monitoring System
Refined MariaDB SQL script

Based on the team's original SQL submission. This version preserves the eight
core tables, sample entities, three views, original trigger/function/procedure
concepts, and adds safer constraints, indexes, a missing status-label function,
and useful demonstration queries.

IMPORTANT:
- Import into a NEW/EMPTY schema. This script does not DROP an existing database
  or tables and is not intended to overwrite an existing populated schema.
- XAMPP uses MariaDB. Check the MariaDB version in phpMyAdmin before import.
- Seed password_hash values below are placeholders, not login-ready passwords.
  The Flask application must create real password hashes before enabling login.
- A trigger cannot fire merely because time passes. The expiry trigger checks
  the expiry date when a subscription is inserted or updated. For scheduled
  expiry processing, a MariaDB EVENT can be added separately if desired.
===============================================================================
*/

CREATE DATABASE IF NOT EXISTS api_management
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE api_management;

/* ---------------------------------------------------------------------------
   1. TABLES (DDL)
   --------------------------------------------------------------------------- */

CREATE TABLE `ROLE` (
    role_id INT NOT NULL AUTO_INCREMENT,
    role_name VARCHAR(50) NOT NULL,
    description VARCHAR(255) NULL,
    PRIMARY KEY (role_id),
    UNIQUE KEY uq_role_name (role_name)
) ENGINE=InnoDB;

CREATE TABLE TEAM (
    team_id INT NOT NULL AUTO_INCREMENT,
    team_name VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL,
    PRIMARY KEY (team_id),
    UNIQUE KEY uq_team_name (team_name)
) ENGINE=InnoDB;

CREATE TABLE `USER` (
    user_id INT NOT NULL AUTO_INCREMENT,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    phone VARCHAR(15) NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,
    team_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_user_email (email),
    KEY idx_user_role (role_id),
    KEY idx_user_team (team_id),
    KEY idx_user_status (status),
    CONSTRAINT fk_user_role FOREIGN KEY (role_id)
        REFERENCES `ROLE` (role_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_user_team FOREIGN KEY (team_id)
        REFERENCES TEAM (team_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE API (
    api_id INT NOT NULL AUTO_INCREMENT,
    api_name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    category VARCHAR(50) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    owner_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (api_id),
    UNIQUE KEY uq_api_name (api_name),
    KEY idx_api_owner (owner_id),
    KEY idx_api_status (status),
    KEY idx_api_category (category),
    CONSTRAINT fk_api_owner FOREIGN KEY (owner_id)
        REFERENCES `USER` (user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE API_VERSION (
    version_id INT NOT NULL AUTO_INCREMENT,
    api_id INT NOT NULL,
    version_number VARCHAR(20) NOT NULL,
    release_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    changelog TEXT NULL,
    deprecated_date DATE NULL,
    PRIMARY KEY (version_id),
    UNIQUE KEY uq_api_version (api_id, version_number),
    /* Supports a composite FK from SUBSCRIPTION, ensuring the chosen version
       belongs to the same API selected by that subscription. */
    UNIQUE KEY uq_version_api_pair (version_id, api_id),
    KEY idx_version_api_status (api_id, status),
    CONSTRAINT fk_version_api FOREIGN KEY (api_id)
        REFERENCES API (api_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE ENDPOINT (
    endpoint_id INT NOT NULL AUTO_INCREMENT,
    version_id INT NOT NULL,
    method VARCHAR(10) NOT NULL,
    endpoint_path VARCHAR(255) NOT NULL,
    description TEXT NULL,
    PRIMARY KEY (endpoint_id),
    UNIQUE KEY uq_endpoint_version_method_path
        (version_id, method, endpoint_path),
    KEY idx_endpoint_version (version_id),
    CONSTRAINT fk_endpoint_version FOREIGN KEY (version_id)
        REFERENCES API_VERSION (version_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE SUBSCRIPTION (
    subscription_id INT NOT NULL AUTO_INCREMENT,
    api_id INT NOT NULL,
    version_id INT NOT NULL,
    consumer_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    subscribe_date DATE NOT NULL,
    expires_at DATE NULL,
    PRIMARY KEY (subscription_id),
    KEY idx_subscription_api (api_id),
    KEY idx_subscription_version_api (version_id, api_id),
    KEY idx_subscription_consumer (consumer_id),
    KEY idx_subscription_status_expiry (status, expires_at),
    CONSTRAINT fk_subscription_api FOREIGN KEY (api_id)
        REFERENCES API (api_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    /* Composite FK prevents pairing API A with a version belonging to API B. */
    CONSTRAINT fk_subscription_version_api FOREIGN KEY (version_id, api_id)
        REFERENCES API_VERSION (version_id, api_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_subscription_consumer FOREIGN KEY (consumer_id)
        REFERENCES `USER` (user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE PERMISSION (
    permission_id INT NOT NULL AUTO_INCREMENT,
    subscription_id INT NOT NULL,
    permission_type VARCHAR(50) NOT NULL,
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (permission_id),
    UNIQUE KEY uq_subscription_permission (subscription_id, permission_type),
    KEY idx_permission_allowed (allowed),
    CONSTRAINT fk_permission_subscription FOREIGN KEY (subscription_id)
        REFERENCES SUBSCRIPTION (subscription_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

/* ---------------------------------------------------------------------------
   2. SAMPLE DATA (DML)
   IDs are explicit to keep the original report's sample relationships.
   --------------------------------------------------------------------------- */

INSERT INTO `ROLE` (role_id, role_name, description) VALUES
(1, 'Admin', 'Manages the entire API management system'),
(2, 'Developer', 'Develops and manages APIs'),
(3, 'Consumer', 'Uses and subscribes to APIs');

INSERT INTO TEAM (team_id, team_name, description) VALUES
(1, 'Platform Team', 'Manages API infrastructure'),
(2, 'Payment Team', 'Develops and manages payment APIs'),
(3, 'Mobile Team', 'Develops mobile applications');

INSERT INTO `USER`
(user_id, full_name, email, phone, password_hash, role_id, team_id, status)
VALUES
(1, 'Arjun Kumar', 'arjun@company.com', '9876543210', 'REPLACE_WITH_VALID_PASSWORD_HASH_1', 1, 1, 'ACTIVE'),
(2, 'Rahul Sharma', 'rahul@company.com', '9876543211', 'REPLACE_WITH_VALID_PASSWORD_HASH_2', 2, 2, 'ACTIVE'),
(3, 'Priya Nair', 'priya@company.com', '9876543212', 'REPLACE_WITH_VALID_PASSWORD_HASH_3', 2, 3, 'ACTIVE'),
(4, 'Kiran Rao', 'kiran@company.com', '9876543213', 'REPLACE_WITH_VALID_PASSWORD_HASH_4', 3, 3, 'ACTIVE'),
(5, 'Sneha Patel', 'sneha@company.com', '9876543214', 'REPLACE_WITH_VALID_PASSWORD_HASH_5', 3, 2, 'ACTIVE');

INSERT INTO API
(api_id, api_name, description, category, status, owner_id)
VALUES
(1, 'Payment API', 'Provides payment processing and transaction services', 'Finance', 'ACTIVE', 2),
(2, 'User Authentication API', 'Provides user login and authentication services', 'Security', 'ACTIVE', 1),
(3, 'Notification API', 'Provides email and SMS notification services', 'Communication', 'ACTIVE', 1),
(4, 'Product API', 'Provides product information and catalog services', 'Commerce', 'ACTIVE', 3);

INSERT INTO API_VERSION
(version_id, api_id, version_number, release_date, status, changelog, deprecated_date)
VALUES
(1, 1, 'v1', '2025-01-15', 'DEPRECATED', 'Initial payment API release', '2026-01-01'),
(2, 1, 'v2', '2026-01-10', 'ACTIVE', 'Improved payment processing and security', NULL),
(3, 2, 'v1', '2025-03-20', 'ACTIVE', 'Initial authentication API', NULL),
(4, 3, 'v1', '2025-06-10', 'ACTIVE', 'Initial notification API', NULL),
(5, 4, 'v1', '2026-02-15', 'ACTIVE', 'Initial product API', NULL);

INSERT INTO ENDPOINT
(endpoint_id, version_id, method, endpoint_path, description)
VALUES
(1, 2, 'POST', '/payments', 'Create a new payment'),
(2, 2, 'GET', '/payments/{id}', 'Retrieve payment details'),
(3, 2, 'DELETE', '/payments/{id}', 'Cancel a payment'),
(4, 3, 'POST', '/login', 'Authenticate a user'),
(5, 3, 'POST', '/logout', 'Log out a user'),
(6, 4, 'POST', '/notifications', 'Send a notification'),
(7, 5, 'GET', '/products', 'Retrieve all products'),
(8, 5, 'GET', '/products/{id}', 'Retrieve product details');

INSERT INTO SUBSCRIPTION
(subscription_id, api_id, version_id, consumer_id, status, subscribe_date, expires_at)
VALUES
(1, 1, 2, 4, 'ACTIVE', '2026-03-01', '2027-03-01'),
(2, 2, 3, 4, 'ACTIVE', '2026-03-01', '2027-03-01'),
(3, 3, 4, 4, 'ACTIVE', '2026-03-05', '2027-03-05'),
(4, 1, 2, 5, 'ACTIVE', '2026-04-10', '2027-04-10'),
(5, 4, 5, 5, 'ACTIVE', '2026-04-15', '2027-04-15');

INSERT INTO PERMISSION
(permission_id, subscription_id, permission_type, allowed)
VALUES
(1, 1, 'READ', TRUE),
(2, 1, 'WRITE', TRUE),
(3, 2, 'READ', TRUE),
(4, 2, 'WRITE', TRUE),
(5, 3, 'WRITE', TRUE),
(6, 4, 'READ', TRUE),
(7, 5, 'READ', TRUE);

/* ---------------------------------------------------------------------------
   3. VIEWS
   Drop/recreate only the views so this section can be re-run independently.
   --------------------------------------------------------------------------- */

DROP VIEW IF EXISTS subscription_details_view;
DROP VIEW IF EXISTS api_version_view;
DROP VIEW IF EXISTS api_details_view;

CREATE VIEW api_details_view AS
SELECT
    A.api_id,
    A.api_name,
    A.description,
    A.category,
    A.status,
    A.owner_id,
    U.full_name AS owner_name,
    U.email AS owner_email,
    A.created_at
FROM API A
JOIN `USER` U ON A.owner_id = U.user_id;

CREATE VIEW api_version_view AS
SELECT
    V.version_id,
    A.api_id,
    A.api_name,
    V.version_number,
    V.release_date,
    V.status,
    V.changelog,
    V.deprecated_date
FROM API A
JOIN API_VERSION V ON A.api_id = V.api_id;

CREATE VIEW subscription_details_view AS
SELECT
    S.subscription_id,
    S.api_id,
    S.version_id,
    S.consumer_id,
    U.full_name AS consumer_name,
    U.email AS consumer_email,
    A.api_name,
    V.version_number,
    S.status AS subscription_status,
    S.subscribe_date,
    S.expires_at
FROM SUBSCRIPTION S
JOIN `USER` U ON S.consumer_id = U.user_id
JOIN API A ON S.api_id = A.api_id
JOIN API_VERSION V ON S.version_id = V.version_id AND S.api_id = V.api_id;

/* ---------------------------------------------------------------------------
   4. TRIGGERS
   --------------------------------------------------------------------------- */

DROP TRIGGER IF EXISTS after_api_deprecated;
DROP TRIGGER IF EXISTS check_subscription_expiry;
DROP TRIGGER IF EXISTS check_subscription_expiry_insert;

DELIMITER //

/* Original trigger concept: when an API becomes deprecated, deprecate its
   currently active versions automatically. */
CREATE TRIGGER after_api_deprecated
AFTER UPDATE ON API
FOR EACH ROW
BEGIN
    IF NEW.status = 'DEPRECATED'
       AND OLD.status <> 'DEPRECATED' THEN
        UPDATE API_VERSION
        SET status = 'DEPRECATED',
            deprecated_date = COALESCE(deprecated_date, CURDATE())
        WHERE api_id = NEW.api_id
          AND status = 'ACTIVE';
    END IF;
END//

/* Preserve the original UPDATE trigger name and improve it so an expired
   subscription cannot be left ACTIVE when its row is updated. */
CREATE TRIGGER check_subscription_expiry
BEFORE UPDATE ON SUBSCRIPTION
FOR EACH ROW
BEGIN
    IF NEW.expires_at IS NOT NULL AND NEW.expires_at < CURDATE() THEN
        SET NEW.status = 'EXPIRED';
    END IF;
END//

/* Additional INSERT trigger: also catches already-expired subscriptions
   at the moment they are created. */
CREATE TRIGGER check_subscription_expiry_insert
BEFORE INSERT ON SUBSCRIPTION
FOR EACH ROW
BEGIN
    IF NEW.expires_at IS NOT NULL AND NEW.expires_at < CURDATE() THEN
        SET NEW.status = 'EXPIRED';
    END IF;
END//

DELIMITER ;

/* ---------------------------------------------------------------------------
   5. STORED FUNCTIONS
   --------------------------------------------------------------------------- */

DROP FUNCTION IF EXISTS api_status_label;
DROP FUNCTION IF EXISTS api_age;
DROP FUNCTION IF EXISTS subscription_days;

DELIMITER //

/* CURDATE() changes over time, so api_age must not be declared DETERMINISTIC. */
CREATE FUNCTION api_age(api_date DATE)
RETURNS INT
NOT DETERMINISTIC
NO SQL
BEGIN
    IF api_date IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN TIMESTAMPDIFF(YEAR, api_date, CURDATE());
END//

CREATE FUNCTION subscription_days(start_date DATE, end_date DATE)
RETURNS INT
DETERMINISTIC
NO SQL
BEGIN
    IF start_date IS NULL OR end_date IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN DATEDIFF(end_date, start_date);
END//

/* This function was referenced by the original SQL test query but its
   definition was missing. Added so the supplied test query can execute. */
CREATE FUNCTION api_status_label(api_status VARCHAR(20))
RETURNS VARCHAR(50)
DETERMINISTIC
NO SQL
BEGIN
    RETURN CASE UPPER(COALESCE(api_status, ''))
        WHEN 'ACTIVE' THEN 'API is active'
        WHEN 'DEPRECATED' THEN 'API is deprecated'
        WHEN 'MAINTENANCE' THEN 'API is under maintenance'
        WHEN 'INACTIVE' THEN 'API is inactive'
        ELSE 'Unknown API status'
    END;
END//

DELIMITER ;

/* ---------------------------------------------------------------------------
   6. STORED PROCEDURES
   --------------------------------------------------------------------------- */

DROP PROCEDURE IF EXISTS get_apis_by_owner;
DROP PROCEDURE IF EXISTS get_api_subscriptions;

DELIMITER //

CREATE PROCEDURE get_apis_by_owner(IN ownerId INT)
BEGIN
    SELECT api_id, api_name, category, status, created_at
    FROM API
    WHERE owner_id = ownerId
    ORDER BY api_name;
END//

CREATE PROCEDURE get_api_subscriptions(IN apiId INT)
BEGIN
    SELECT
        A.api_name,
        U.full_name AS consumer,
        V.version_number,
        S.status,
        S.subscribe_date,
        S.expires_at
    FROM SUBSCRIPTION S
    JOIN API A ON S.api_id = A.api_id
    JOIN `USER` U ON S.consumer_id = U.user_id
    JOIN API_VERSION V ON S.version_id = V.version_id AND S.api_id = V.api_id
    WHERE S.api_id = apiId
    ORDER BY S.subscribe_date DESC, S.subscription_id DESC;
END//

DELIMITER ;

/* ---------------------------------------------------------------------------
   7. DEMONSTRATION / REPORT QUERIES (read-only)
   These SELECT statements are safe to run repeatedly.
   --------------------------------------------------------------------------- */

-- Basic table reads
SELECT * FROM `ROLE`;
SELECT * FROM TEAM;
SELECT user_id, full_name, email, phone, role_id, team_id, status, created_at FROM `USER`;
SELECT * FROM API;
SELECT * FROM API_VERSION;
SELECT * FROM ENDPOINT;
SELECT * FROM SUBSCRIPTION;
SELECT * FROM PERMISSION;

-- JOIN: API with owner
SELECT A.api_name, U.full_name AS owner_name, A.category, A.status
FROM API A
JOIN `USER` U ON A.owner_id = U.user_id;

-- JOIN: API versions
SELECT A.api_name, V.version_number, V.status, V.release_date
FROM API A
JOIN API_VERSION V ON A.api_id = V.api_id;

-- JOIN: subscription details
SELECT U.full_name AS consumer, A.api_name, V.version_number,
       S.status, S.subscribe_date, S.expires_at
FROM SUBSCRIPTION S
JOIN `USER` U ON S.consumer_id = U.user_id
JOIN API A ON S.api_id = A.api_id
JOIN API_VERSION V ON S.version_id = V.version_id AND S.api_id = V.api_id;

-- GROUP BY: number of versions per API (includes APIs with zero versions)
SELECT A.api_name, COUNT(V.version_id) AS total_versions
FROM API A
LEFT JOIN API_VERSION V ON A.api_id = V.api_id
GROUP BY A.api_id, A.api_name;

-- GROUP BY: number of subscriptions per API
SELECT A.api_name, COUNT(S.subscription_id) AS total_subscriptions
FROM API A
LEFT JOIN SUBSCRIPTION S ON A.api_id = S.api_id
GROUP BY A.api_id, A.api_name;

-- HAVING: APIs with more than one subscription
SELECT A.api_name, COUNT(S.subscription_id) AS total_subscriptions
FROM API A
JOIN SUBSCRIPTION S ON A.api_id = S.api_id
GROUP BY A.api_id, A.api_name
HAVING COUNT(S.subscription_id) > 1;

-- Subquery: APIs that have subscriptions
SELECT api_name FROM API
WHERE api_id IN (SELECT api_id FROM SUBSCRIPTION);

-- Subquery: APIs that have no subscriptions (NOT EXISTS avoids NULL issues)
SELECT A.api_name FROM API A
WHERE NOT EXISTS (
    SELECT 1 FROM SUBSCRIPTION S WHERE S.api_id = A.api_id
);

-- Aggregate functions: count, sum, average, minimum and maximum
SELECT
    COUNT(*) AS total_apis,
    SUM(status = 'ACTIVE') AS active_apis,
    AVG(api_id) AS average_api_id,
    MIN(created_at) AS first_api_created,
    MAX(created_at) AS latest_api_created
FROM API;

-- Function demonstrations
SELECT api_id, api_name, api_age(DATE(created_at)) AS age_in_years
FROM API;

SELECT subscription_id,
       subscription_days(subscribe_date, expires_at) AS subscription_duration_days
FROM SUBSCRIPTION;

SELECT api_name, api_status_label(status) AS status_description
FROM API;

-- View demonstrations
SELECT * FROM api_details_view;
SELECT * FROM api_version_view;
SELECT * FROM subscription_details_view;

-- Procedure demonstrations
CALL get_apis_by_owner(1);
CALL get_api_subscriptions(1);

/* ---------------------------------------------------------------------------
   8. SAFE MANUAL TRIGGER DEMONSTRATIONS

   Run these separately only when you want to demonstrate triggers. They change
   data, so do not execute them as part of routine application startup.

   A. API deprecation trigger test (choose a disposable/test API in your own DB):
      SELECT api_id, status FROM API WHERE api_id = 1;
      SELECT version_id, version_number, status FROM API_VERSION WHERE api_id = 1;
      UPDATE API SET status = 'DEPRECATED' WHERE api_id = 1;
      SELECT version_id, version_number, status, deprecated_date
      FROM API_VERSION WHERE api_id = 1;

   B. Subscription expiry trigger test (use a test subscription row):
      UPDATE SUBSCRIPTION
      SET expires_at = DATE_SUB(CURDATE(), INTERVAL 1 DAY), status = 'ACTIVE'
      WHERE subscription_id = 1;
      SELECT subscription_id, status, expires_at
      FROM SUBSCRIPTION WHERE subscription_id = 1;
      The BEFORE UPDATE trigger should set status to EXPIRED.

   Note: To demonstrate expiry without modifying original sample rows, insert a
   separate test subscription with valid API/version/consumer IDs and a past
   expires_at date. The BEFORE INSERT trigger should set it to EXPIRED.
   --------------------------------------------------------------------------- */

/* ---------------------------------------------------------------------------
   9. DDL / DML EXAMPLES FOR THE DBMS CONCEPTS PAGE (commented; not auto-run)

   DDL:
      ALTER TABLE API ADD COLUMN documentation_url VARCHAR(255) NULL;
      -- If used as a demo, remove it afterwards with a matching ALTER TABLE DROP.

   DML:
      INSERT INTO TEAM (team_name, description)
      VALUES ('Demo Team', 'Temporary demonstration team');
      UPDATE TEAM SET description = 'Updated demo description'
      WHERE team_name = 'Demo Team';
      DELETE FROM TEAM WHERE team_name = 'Demo Team';

   DQL:
      SELECT api_name, category, status FROM API ORDER BY api_name;
   --------------------------------------------------------------------------- */
