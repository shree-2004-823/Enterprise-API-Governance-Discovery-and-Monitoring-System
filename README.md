# Enterprise API Governance, Discovery and Monitoring System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0%20%7C%20MariaDB%2010.4%2B-orange.svg)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-Academic%20Project-green.svg)]()
[![Tests](https://img.shields.io/badge/Automated%20Tests-228%20Passing%20(100%25)-brightgreen.svg)]()

A production-grade, enterprise-ready web application built for API lifecycle governance, discovery, and subscription monitoring. The system demonstrates advanced Relational Database Management System (RDBMS) design, including normalized schemas, complex integrity constraints, triggers, stored functions, stored procedures, views, and an interactive **14-Module DBMS Concepts Laboratory** designed for university DBMS evaluation.

---

## Table of Contents
1. [Key Features](#key-features)
2. [Database Architecture & Schema](#database-architecture--schema)
3. [Prerequisites](#prerequisites)
4. [Step-by-Step Setup Guide](#step-by-step-setup-guide)
   - [Step 1: Clone Repository](#step-1-clone-repository)
   - [Step 2: Create Virtual Environment](#step-2-create-virtual-environment)
   - [Step 3: Install Dependencies](#step-3-install-dependencies)
   - [Step 4: Configure Environment Variables](#step-4-configure-environment-variables)
   - [Step 5: Initialize the Database](#step-5-initialize-the-database)
   - [Step 6: Run the Application](#step-6-run-the-application)
5. [Demo User Credentials (RBAC)](#demo-user-credentials-rbac)
6. [Interactive DBMS Laboratory (14 Modules)](#interactive-dbms-laboratory-14-modules)
7. [Reports & Analytics Dashboard](#reports--analytics-dashboard)
8. [Automated Verification Test Suite](#automated-verification-test-suite)
9. [Troubleshooting & FAQs](#troubleshooting--faqs)
10. [Project Directory Structure](#project-directory-structure)

---

## Key Features

- **Full API Lifecycle Management**: Create, publish, manage, version, and deprecate APIs with automated cascading deprecation handled directly inside the database engine.
- **Consumer Subscription & Key Provisioning**: Self-service API discovery, subscription requests, and 32-character hex API key provisioning.
- **Automated Expiry Governance**: Active database triggers intercept expired subscriptions on insert and update; a server-side expiry sweep triggers live database evaluations.
- **14-Module Interactive DBMS Laboratory**: An in-browser interactive laboratory allowing students and evaluators to execute, inspect, and verify real SQL operations (DDL, DML, Transactions, Joins, Triggers, Procedures, and Views) with live execution and safe transactional rollbacks.
- **Enterprise Reports & Analytics**: Interactive charts and 15 analytical reporting modules for executive visibility into API inventory, HTTP methods, team governance, and subscription urgency.
- **Strict Security & RBAC**:
  - Role-Based Access Control (`ADMIN`, `DEVELOPER`, `CONSUMER`).
  - Session-based CSRF protection on all mutating state changes.
  - Salted SHA-256 password hashing via Werkzeug security.
  - Parameterized queries throughout (zero SQL injection vulnerability).

---

## Database Architecture & Schema

The underlying database engine executes all core business logic. **Python and JavaScript never simulate or duplicate database logic.**

```
+---------------------------------------------------------------------------------+
|                                api_management                                   |
+---------------------------------------------------------------------------------+
|  TABLES (8):                                                                    |
|    - USER (user_id, team_id, name, email, password_hash, role, created_at)      |
|    - TEAM (team_id, team_name, created_at)                                      |
|    - API (api_id, owner_id, name, description, category, status, created_at)    |
|    - API_VERSION (version_id, api_id, version_num, status, release_notes, ...)  |
|    - ENDPOINT (endpoint_id, version_id, path, http_method, description, ...)    |
|    - SUBSCRIPTION (subscription_id, user_id, api_id, tier, status, ...)         |
|    - AUDIT_LOG (log_id, action, entity_type, entity_id, user_id, timestamp)     |
|    - API_KEY (key_id, subscription_id, key_hash, is_active, created_at)        |
|                                                                                 |
|  RELATIONAL CONSTRAINTS:                                                        |
|    - 9 Foreign Keys (RESTRICT on critical parents, CASCADE on dependents)       |
|    - UNIQUE constraints (email, team name, API per owner, version per API)     |
|    - CHECK constraints & ENUM domain validation                                 |
|                                                                                 |
|  DATABASE VIEWS (3):                                                            |
|    - api_details_view                                                           |
|    - api_version_view                                                           |
|    - subscription_details_view                                                  |
|                                                                                 |
|  STORED FUNCTIONS (3):                                                          |
|    - api_age(created_date) -> INT (calculates age in days via DATEDIFF)         |
|    - subscription_days(start_date, expires_date) -> INT                         |
|    - api_status_label(status) -> VARCHAR                                        |
|                                                                                 |
|  STORED PROCEDURES (2):                                                         |
|    - get_apis_by_owner(IN p_owner_id INT)                                       |
|    - get_api_subscriptions(IN p_api_id INT)                                     |
|                                                                                 |
|  BUSINESS TRIGGERS (3):                                                         |
|    - after_api_deprecated: Cascades status to DEPRECATED across versions       |
|    - check_subscription_expiry: BEFORE UPDATE sets status = EXPIRED             |
|    - check_subscription_expiry_insert: BEFORE INSERT sets status = EXPIRED      |
+---------------------------------------------------------------------------------+
```

---

## Prerequisites

Before running the project, ensure you have the following installed on your machine:

1. **Python 3.10+** (Python 3.11 or 3.12 recommended)
   - Check with: `python --version`
2. **Database Engine** (Choose one):
   - **Option A (Recommended for production/standalone)**: **MySQL Server 8.0+**
   - **Option B (Recommended for student XAMPP setups)**: **XAMPP** (with MariaDB 10.4+)
3. **Git**
   - Check with: `git --version`

---

## Step-by-Step Setup Guide

### Step 1: Clone Repository

```bash
git clone https://github.com/shree-2004-823/Enterprise-API-Governance-Discovery-and-Monitoring-System.git
cd Enterprise-API-Governance-Discovery-and-Monitoring-System
```

---

### Step 2: Create Virtual Environment

Isolate the project packages by setting up a Python virtual environment:

**On Windows (PowerShell or Command Prompt):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**On macOS / Linux (bash or zsh):**
```bash
python3 -m venv venv
source venv/bin/activate
```

*(You will see `(venv)` prepended to your command prompt).*

---

### Step 3: Install Dependencies

Install all required Python packages with `pip`:

```bash
pip install -r requirements.txt
```

*Packages installed:*
- `Flask>=3.0.0`: Web framework, template routing, and session management.
- `PyMySQL>=1.1.0`: Pure-Python MySQL client library.
- `python-dotenv>=1.0.0`: Environment variable loader from local `.env` files.

---

### Step 4: Configure Environment Variables

Create your local `.env` configuration file by copying `.env.example`:

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**On macOS / Linux:**
```bash
cp .env.example .env
```

Now open `.env` in any text editor and adjust your database connection credentials:

#### For MySQL Server 8.0 (Existing MySQL Installation)
```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_root_password
DB_NAME=api_management
SECRET_KEY=9a4f61f7d3a2e5c8b104928e75fa3d12c849102837465abcde9012345678cafe
```

#### For XAMPP (MariaDB default installation)
```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=api_management
SECRET_KEY=9a4f61f7d3a2e5c8b104928e75fa3d12c849102837465abcde9012345678cafe
```

> **Tip:** You can generate a fresh random `SECRET_KEY` in terminal with:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

### Step 5: Initialize the Database

Run the automated database setup script:

```bash
python setup_db.py
```

#### What `setup_db.py` does:
1. Connects to your running MySQL/MariaDB server using credentials in `.env`.
2. Automatically ensures `log_bin_trust_function_creators = 1` for MySQL 8.0 stored functions.
3. Parses and executes `sql/api_management_refined.sql` directly:
   - Creates the `api_management` database schema.
   - Builds all 8 tables and 9 foreign key constraints.
   - Inserts rich enterprise sample seed data (teams, users, APIs, endpoints, subscriptions).
   - Compiles all 3 Views, 3 Triggers, 3 Stored Functions, and 2 Stored Procedures.
4. Generates valid salted password hashes (`Password@123`) for all seed user accounts.

#### Helpful Setup Flags:
- **Reset Database**: To wipe and cleanly rebuild the database from scratch at any time:
  ```bash
  python setup_db.py --reset
  ```
- **Hashes Only**: If you imported `sql/api_management_refined.sql` manually via phpMyAdmin or MySQL Workbench:
  ```bash
  python setup_db.py --hashes-only
  ```

---

### Step 6: Run the Application

Start the Flask development server:

```bash
python app.py
```

Expected output:
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

Open your browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Demo User Credentials (RBAC)

The system includes pre-seeded user accounts for each organizational role. All accounts share the same demo password:

**Default Password for all accounts:** `Password@123`

| Name | Role | Email | Permissions |
| :--- | :--- | :--- | :--- |
| **Arjun Mehta** | `ADMIN` | `arjun@company.com` | Full administrative control: user management, global API status overrides, database expiry sweep, all reports |
| **Rahul Sharma** | `DEVELOPER` | `rahul@company.com` | Create and manage own APIs, create versions, define endpoints, manage subscriptions |
| **Priya Patel** | `DEVELOPER` | `priya@company.com` | Manage Core Payment and Analytics APIs, version lifecycles, and developer governance |
| **Kiran Rao** | `CONSUMER` | `kiran@company.com` | Browse API Catalog, subscribe to APIs, view and manage provisioned API Keys (read-only) |
| **Sneha Joshi** | `CONSUMER` | `sneha@company.com` | Self-service API discovery and subscription management (read-only) |

---

## Interactive DBMS Laboratory (14 Modules)

Navigate to **DBMS Concepts** in the sidebar (`/concepts`) to interact with the interactive learning laboratory. Built specifically for university evaluations and project vivas, every module presents:
1. Concept explanation and theoretical justification.
2. The exact SQL query executed.
3. A line-by-line syntax and relational mechanics breakdown table.
4. An interactive **Demonstrate** button that executes live against MySQL and renders real before/after records.

| # | Concept Module | Real MySQL Demonstration |
|---|---|---|
| **1** | **Database Overview & Architecture** | Queries `information_schema.TABLES` for storage engines, collation, and `SHOW CREATE TABLE API`. |
| **2** | **Tables & Integrity Constraints** | Tests `UNIQUE`, `NOT NULL`, and `DEFAULT` constraints; catches MySQL errors `1062` and `1048`. |
| **3** | **Primary Keys & Foreign Keys** | Evaluates referential integrity rules (`ON DELETE RESTRICT` vs `CASCADE`); demonstrates MySQL errors `1451` and `1452`. |
| **4** | **Data Definition Language (DDL)** | Executes live lifecycle: `CREATE TABLE`, `ALTER TABLE ADD COLUMN`, `ALTER TABLE DROP COLUMN`, and `DROP TABLE`. |
| **5** | **Data Manipulation Language (DML)** | Executes `INSERT`, `UPDATE`, `DELETE`, and demonstrates ACID atomicity with manual `ROLLBACK`. |
| **6** | **SELECT Queries & Data Filtering** | Evaluates column projection, pattern matching with `LIKE`, and range filtering with `BETWEEN`. |
| **7** | **JOIN Operations** | Compares `INNER JOIN` (strict intersection) vs `LEFT JOIN` (preserves unmatched records). |
| **8** | **Aggregate Functions** | Demonstrates `COUNT()`, `SUM()`, `AVG()`, `MIN()`, and `MAX()` on endpoints and subscriptions. |
| **9** | **GROUP BY and HAVING Clauses** | Groups metrics per API and filters aggregated groups using `HAVING COUNT(*) > 1`. |
| **10** | **Advanced Subqueries** | Executes Scalar subqueries, Membership `IN`, Correlated `NOT EXISTS`, and Derived Tables. |
| **11** | **Database Views (Virtual Tables)** | Queries pre-compiled views (`api_details_view`, `api_version_view`, `subscription_details_view`). |
| **12** | **Stored Functions** | Live invocation of `api_age()`, `subscription_days()`, and `api_status_label()`. |
| **13** | **Stored Procedures** | Executes `CALL get_apis_by_owner(?)` and `CALL get_api_subscriptions(?)`. |
| **14** | **Active Database Triggers** | Demonstrates `after_api_deprecated` cascading status updates and time-travel subscription expiry sweeps. |

---

## Reports & Analytics Dashboard

Access **Reports** in the sidebar (`/reports`) for executive telemetry:
- **Executive KPI Cards**: Total APIs, Total Versions, Total Endpoints, Subscriptions, Registered Users.
- **Visual Analytics**: Interactive distribution of APIs by Category and Endpoints by HTTP Method.
- **Subscription Expiry Telemetry**: Identifies active, urgent (expiring soon), and expired subscriptions with calculated remaining days.
- **Version Lifecycle & Owner Governance**: Aggregated version statuses and API counts grouped by engineering teams.
- **Instant Client-Side Search**: Filter through all 15 relational reports instantly in real-time.

---

## Automated Verification Test Suite

The project includes three comprehensive automated test suites covering database schema, web routing, security, and laboratory demonstrations.

Run all test suites inside your virtual environment:

```powershell
# 1. Database Schema & Object Integrity (98 assertions)
python test_database.py

# 2. Flask GUI, Routing, and RBAC (69 assertions)
python test_app.py

# 3. Phase 2 Enhancements, Reports, CSRF, and 14 Laboratory Modules (61 assertions)
python test_phase2.py
```

### Combined Test Results:
```
================================================================================
Test Suite                             Checks Passed    Coverage
--------------------------------------------------------------------------------
1. test_database.py                     98 / 98         Tables, FKs, Views, Triggers, Procs, Funcs
2. test_app.py                          69 / 69         Routes, Logins, RBAC, CRUD, Error Handling
3. test_phase2.py                       61 / 61         Navigation, Reports, CSRF, 14 Lab Concepts
================================================================================
TOTAL AUTOMATED TEST VERIFICATIONS:    228 / 228 (100% PASS)
================================================================================
```

---

## Troubleshooting & FAQs

### Q1: `Error 1418: This function has none of DETERMINISTIC, NO SQL, or READS SQL DATA in its declaration and binary logging is enabled`
- **Cause**: MySQL 8.0 has binary logging enabled by default and requires authorization for stored function creators.
- **Solution**: `setup_db.py` attempts this automatically. If you run into permissions issues, execute this single query in MySQL Workbench or mysql CLI as root:
  ```sql
  SET GLOBAL log_bin_trust_function_creators = 1;
  ```

### Q2: `Access denied for user 'root'@'localhost'`
- **Cause**: The password in `.env` does not match your MySQL server's root password.
- **Solution**: Open `.env` and verify `DB_PASSWORD=your_actual_password`. Ensure there are no accidental spaces.

### Q3: `Port 3306 in use or Cannot connect to MySQL`
- **Cause**: Another database service (or XAMPP) is running on port 3306.
- **Solution**: Check Windows Services (`services.msc`) for `MySQL80` or start MySQL in the XAMPP Control Panel. If MySQL is running on port 3307, change `DB_PORT=3307` in your `.env`.

### Q4: `400 Bad Request - Invalid CSRF Token`
- **Cause**: Session expired or CSRF token not included in POST request.
- **Solution**: In Phase 2, CSRF token handling is globally injected into Jinja macros (`csrf_token()`). Refresh the page and ensure cookies are enabled in your browser.

---

## Project Directory Structure

```
Enterprise-API-Governance-Discovery-and-Monitoring-System/
├── .env.example               # Template environment configuration file
├── .gitignore                  # Git ignore rules (protects credentials and venvs)
├── README.md                   # Complete system documentation and setup guide
├── requirements.txt            # Python dependencies (Flask, PyMySQL, python-dotenv)
├── config.py                   # Application settings & database connection loader
├── db.py                       # PyMySQL connection factory & cursor helpers
├── setup_db.py                 # Automated SQL importer, function enabler, and hasher
├── app.py                      # Core Flask application, route handlers & CSRF protection
├── concepts.py                 # 14 DBMS Laboratory demonstration modules & query engine
├── reports_data.py             # Analytical queries & telemetry generation for reports
├── test_database.py            # 98-check database verification test suite
├── test_app.py                 # 69-check application GUI and route test suite
├── test_phase2.py              # 61-check Phase 2 verification test suite
├── sql/
│   └── api_management_refined.sql  # Canonical SQL schema, tables, views, triggers, procs
├── static/
│   ├── css/
│   │   └── style.css           # Modern navy/slate responsive UI stylesheet
│   └── js/
│       └── app.js              # Client-side validation, search filter & notifications
└── templates/
    ├── base.html               # Main layout template with sidebar navigation
    ├── _macros.html            # Reusable UI macros (CSRF inputs, badges, cards)
    ├── login.html              # Authentication login view
    ├── dashboard.html          # Executive system dashboard
    ├── apis.html               # API catalog and discovery
    ├── api_detail.html         # Detailed API view with versions & endpoints
    ├── versions.html           # Version management view
    ├── endpoints.html          # Endpoint management view
    ├── subscriptions.html      # Subscription management & expiry sweep view
    ├── subscription_detail.html# Subscription key details
    ├── users.html              # User management & team assignments (Admin only)
    ├── reports.html            # Analytics dashboard with charts & 15 report tables
    └── concepts.html           # 14-Module DBMS interactive laboratory view
```

---

## Authors & Academic Integrity

Developed for Academic DBMS Mini-Project Evaluation.
- **Database Engine**: MySQL Server 8.0 / MariaDB 10.4+
- **Application Server**: Python 3.11 / Flask 3.0
- **Testing Standard**: Complete automated test coverage with live transactional verification.
