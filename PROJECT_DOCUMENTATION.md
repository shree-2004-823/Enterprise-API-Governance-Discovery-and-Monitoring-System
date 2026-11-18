# Enterprise API Governance, Discovery and Monitoring System

## 1. Project abstract

The Enterprise API Governance, Discovery and Monitoring System is a database-backed web application for keeping track of APIs and their lifecycle data. It provides pages to manage APIs, versions, endpoints, subscriptions, permissions, and users, alongside reports and interactive DBMS demonstrations. A Flask application presents the user interface and sends SQL to MariaDB; relational constraints, views, triggers, stored functions, and stored procedures are defined and executed by the database.

The project is also an educational DBMS demonstration. Its Reports and DBMS Concepts pages present query output and show how relational database features work against the project's own data.

## 2. Problem statement

When API ownership, versions, endpoints, and consumer access are tracked separately or manually, it is difficult to maintain consistent lifecycle information and answer operational questions. Invalid references can also arise unless the database enforces relationships. The project addresses these needs with a relational schema and a web interface that brings the related records and demonstrations together.

## 3. Project objectives

- Maintain API, version, endpoint, user, subscription, and permission records in one relational database.
- Enforce referential integrity and selected uniqueness rules in MariaDB.
- Apply API deprecation and subscription-expiry rules using database triggers.
- Provide reusable calculations and lookups through stored functions and procedures.
- Present joined, grouped, aggregated, and view-based reports.
- Demonstrate DBMS concepts using real database responses.
- Separate read-only Consumer access from Admin and Developer write access.

## 4. Existing system

The project frames the existing-system problem as API lifecycle and subscription data being difficult to manage consistently without a unified interface and database-enforced relationships. In an unintegrated/manual approach, users must assemble information from different records, and rules such as version ownership or expiry handling may be applied inconsistently.

This is the project's motivation, not a claim that a particular external product or organization was evaluated.

## 5. Proposed system

The proposed system stores the domain in eight related tables and serves it through a Flask application. Authenticated users can view API governance data; Admins and Developers can perform supported write operations; Consumers are read-only. MariaDB handles constraints and database programming objects. The interface also includes controlled examples for DDL, DML, joins, subqueries, aggregates, views, triggers, stored functions, and stored procedures.

The concepts demo engine uses server-defined demo keys and typed parameters rather than accepting arbitrary SQL from the browser. Data-changing lessons use a rolled-back transaction or a temporary object, as implemented by the demo.

## 6. Technology stack

| Layer | Technology in this project |
|---|---|
| Frontend | HTML templates, CSS, browser JavaScript |
| Web backend | Python 3 and Flask |
| Database driver | PyMySQL |
| Database | MariaDB in the documented XAMPP setup |
| SQL programming | Tables, foreign keys, views, triggers, stored functions, stored procedures, and queries |

Although the assignment may describe the database as MySQL 8.0, the checked-in README and SQL target a MariaDB/XAMPP setup. The database verification report records MariaDB versions; it should not be presented as a MySQL 8.0 test unless verified separately.

## 7. System architecture

```text
Browser (HTML/CSS/JavaScript)
        |
        | HTTP requests and form/JSON data
        v
Flask application (app.py)
        |                         |
        | parameterized SQL       | predefined demo keys/typed parameters
        v                         v
DB access layer (db.py)     DBMS demo engine (concepts.py)
        \                         /
         \                       /
          v                     v
            MariaDB database
      tables / constraints / views /
       triggers / functions / procedures
```

The templates render data returned by Flask. `db.py` opens request-scoped connections and provides query, write, and stored-procedure helpers. `app.py` implements routes and access checks. `concepts.py` defines allowlisted examples and retrieves database object definitions for the concepts page. `setup_db.py` imports the SQL script and replaces placeholder seed password hashes. `reports_data.py` contains a query-oriented reports data function in the current project tree.

## 8. Database design

The schema is defined in `sql/api_management_refined.sql`. It has eight InnoDB tables:

| Table | Attributes and constraints |
|---|---|
| `ROLE` | `role_id` is the auto-increment primary key; `role_name` and nullable `description`; `role_name` is unique. |
| `TEAM` | `team_id` is the auto-increment primary key; `team_name` and nullable `description`; `team_name` is unique. |
| `USER` | `user_id` is the auto-increment primary key; required name, unique email, password hash, role, and team; nullable phone; status defaults to `ACTIVE`; `created_at` defaults to the current timestamp. `role_id` references `ROLE`; `team_id` references `TEAM`. Both foreign keys cascade parent key updates and restrict parent deletion. |
| `API` | `api_id` is the auto-increment primary key; required name, status (default `ACTIVE`), and owner; nullable description and category; `created_at` defaults to the current timestamp. `api_name` is unique; `owner_id` references `USER`, with update cascade and delete restriction. |
| `API_VERSION` | `version_id` is the auto-increment primary key; required `api_id`, `version_number`, and `release_date`; status defaults to `ACTIVE`; changelog and deprecated date are nullable. `(api_id, version_number)` is unique. `(version_id, api_id)` is also declared unique to support the subscription composite foreign key. `api_id` references `API`, with update and delete cascade. |
| `ENDPOINT` | `endpoint_id` is the auto-increment primary key; required `version_id`, `method`, and `endpoint_path`; description is nullable. `(version_id, method, endpoint_path)` is unique. `version_id` references `API_VERSION`, with update and delete cascade. |
| `SUBSCRIPTION` | `subscription_id` is the auto-increment primary key; required API, version, consumer, and subscribe date; status defaults to `ACTIVE`; expiry date is nullable. `api_id` references `API`; `consumer_id` references `USER`; `(version_id, api_id)` references the corresponding unique pair in `API_VERSION`. All three foreign keys cascade parent key updates and restrict parent deletion. |
| `PERMISSION` | `permission_id` is the auto-increment primary key; required subscription and permission type; `allowed` is a boolean defaulting to true; `created_at` defaults to the current timestamp. `(subscription_id, permission_type)` is unique. `subscription_id` references `SUBSCRIPTION`, with update and delete cascade. |

The schema also declares supporting indexes for foreign keys and selected lookup/filter columns: user role/team/status; API owner/status/category; version API/status; endpoint version; subscription API/version/API/consumer/status/expiry; and permission allowed. `NOT NULL` and `DEFAULT` clauses are defined per column in the SQL. Status columns are `VARCHAR`, not SQL `ENUM` or `CHECK` constraints; supported values are validated in selected application forms.

The full entity-and-relationship diagram is in [DATABASE_ER_DIAGRAM.md](./DATABASE_ER_DIAGRAM.md). The SQL uses primary keys, unique keys, indexes, `NOT NULL`, defaults, and foreign keys. Delete actions include `RESTRICT` where referenced records should not be removed while in use, and `CASCADE` from APIs to versions, versions to endpoints, and subscriptions to permissions. The composite subscription/version key prevents mismatched API/version pairs.

### Views

- `api_details_view` joins each API to its owner in `USER`.
- `api_version_view` joins API metadata to its versions.
- `subscription_details_view` joins subscription data to consumer, API, and version details; its version join also matches the API ID.

These views expose API plus owner fields; version plus API fields; and subscription plus consumer/API/version fields, respectively. They are read models over the base tables, not additional stored copies of those rows.

### Triggers

- `after_api_deprecated`: after an API changes to `DEPRECATED`, updates its currently `ACTIVE` versions to `DEPRECATED` and fills a missing `deprecated_date`.
- `check_subscription_expiry`: before a subscription update, sets its status to `EXPIRED` if a non-null expiry date is before `CURDATE()`.
- `check_subscription_expiry_insert`: applies the same past-expiry rule before an insert.

Triggers run on row writes; they do not execute merely because time passes. The app's expiry sweep issues an update to make MariaDB evaluate the update trigger for overdue active subscriptions.

### Stored functions

- `api_age(api_date)` returns whole years using `TIMESTAMPDIFF(YEAR, api_date, CURDATE())`; a null input returns null. It is declared non-deterministic because the current date changes.
- `subscription_days(start_date, end_date)` returns `DATEDIFF(end_date, start_date)`; a null input returns null.
- `api_status_label(api_status)` maps the supported API statuses to text and returns “Unknown API status” for an unrecognized or null value.

### Stored procedures

- `get_apis_by_owner(ownerId)` returns API records for the given owner, ordered by API name.
- `get_api_subscriptions(apiId)` returns consumer, API, version, status, and subscription-date details for the given API, newest first.

## 9. Module descriptions

- **Authentication and access control (`app.py`)**: login/logout and route-level access checks for authenticated users, writers, and admins.
- **Dashboard**: summary counts, API status grouping, recent versions, and counts of database objects.
- **API management**: list/detail views, create/edit/delete actions, status changes, and owner lookup.
- **Version and endpoint management**: maintain API releases and version-specific endpoint records.
- **Subscription and permission management**: create and update subscriptions, run an expiry sweep, and manage per-subscription permissions.
- **User management**: administrator-only user operations.
- **Reports**: live database-backed summaries and SQL-concept reports.
- **DBMS Concepts laboratory**: allowlisted demos, displayed SQL/results, and live database object definitions.
- **Database setup (`setup_db.py`)**: schema import and seed-account password-hash setup.
- **Database access (`db.py`)**: connection lifecycle, result conversion, parameterized query execution, and stored-procedure result consumption.

## 10. Database concepts implemented

The project demonstrates DDL and DML, primary and foreign keys, unique constraints, referential actions, inner and left joins, grouping and `HAVING`, scalar/`IN`/correlated/derived subqueries, `COUNT`/`SUM`/`AVG`/`MIN`/`MAX`, views, triggers, stored functions, stored procedures, and transactions. The demo descriptions and SQL are in `concepts.py`; the authoritative schema objects are in the SQL script.

## 11. Testing strategy

The repository includes two database-backed test programs:

- `test_database.py` checks schema objects, constraints, trigger behavior, functions, procedures, views, and query results. Its data-changing checks use transactions and rollbacks.
- `test_app.py` exercises Flask routes and role behaviors through the test client, including database-backed create/update flows and cleanup.

The checked-in reports document 98 database checks and 69 GUI checks. These are recorded project results, not results independently rerun while preparing this document. Running the tests requires the configured MariaDB schema and test seed data. Tests should be run on an isolated development database because the GUI test performs real writes and later cleans them up.

## 12. Future enhancements

- Add a proper migration/versioning tool for schema changes.
- Add automated CI using a disposable supported database and clearly stated MySQL/MariaDB compatibility targets.
- Add pagination, search, and API lifecycle audit history for larger datasets.
- Add automated expiry scheduling if the deployment requires it; the current trigger only reacts to writes.
- Add stronger production deployment configuration, secret management, and operational logging.
- Add user-facing validation and automated tests for boundary cases and concurrent updates.
- Expand the permission model if permissions are intended to govern API operations rather than simply be stored and displayed.

## Run locally

Follow the current Windows/XAMPP setup instructions in [README.md](./README.md). Set a strong random `SECRET_KEY` in the process environment or in an ignored local `.env` file before importing the application. In brief: start MariaDB, install requirements, run `python setup_db.py` against an empty schema, then run `python app.py` and open `http://127.0.0.1:5000`. The project's shared seed password is for isolated coursework demos only and must be changed before deployment.
