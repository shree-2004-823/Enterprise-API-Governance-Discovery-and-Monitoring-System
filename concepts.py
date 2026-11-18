"""DBMS Concepts Laboratory Engine.

14 comprehensive DBMS interactive laboratory modules for university evaluation:
1. Database Overview & Architecture
2. Tables and Schema Constraints
3. Primary Keys & Foreign Key Relationships
4. DDL Operations (CREATE, ALTER, DROP)
5. DML Operations (INSERT, UPDATE, DELETE)
6. SELECT Queries & Data Filtering
7. JOIN Operations (INNER & LEFT)
8. Aggregate Functions (COUNT, SUM, AVG, MIN, MAX)
9. GROUP BY and HAVING Clauses
10. Subqueries & Nested Queries
11. Database Views
12. Stored Functions
13. Stored Procedures
14. Database Triggers

Every demo runs real SQL inside MySQL 8.0.
All destructive demonstrations run in transactions that are rolled back,
or on temporary disposable tables that are dropped immediately.
"""
import datetime
import pymysql

from db import clean, clean_rows, connect

TABLES = {
    "ROLE": "SELECT * FROM `ROLE`",
    "TEAM": "SELECT * FROM TEAM",
    "USER": "SELECT user_id, full_name, email, phone, role_id, team_id, status, created_at FROM `USER`",
    "API": "SELECT * FROM API",
    "API_VERSION": "SELECT * FROM API_VERSION",
    "ENDPOINT": "SELECT * FROM ENDPOINT",
    "SUBSCRIPTION": "SELECT * FROM SUBSCRIPTION",
    "PERMISSION": "SELECT * FROM PERMISSION",
}
VIEWS = ["api_details_view", "api_version_view", "subscription_details_view"]

# --------------------------------------------------------------------------
# Plain read-only queries with metadata, line-by-line explanation, and tables
# --------------------------------------------------------------------------
Q = {}


def q(key, title, concept, explain, sql, lines=None, tables=None):
    Q[key] = dict(
        key=key,
        title=title,
        concept=concept,
        explain=explain,
        sql=sql.strip(),
        lines=lines or [],
        tables=tables or [],
    )


# 1. Overview
q("db_objects", "Database Object Inventory", "System Catalog",
  "Queries MySQL's information_schema to verify every object type existing inside the schema.",
  """SELECT 'Base Tables' AS object_type, COUNT(*) AS count FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
UNION ALL SELECT 'Views', COUNT(*) FROM information_schema.VIEWS WHERE TABLE_SCHEMA = DATABASE()
UNION ALL SELECT 'Foreign Keys', COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE()
UNION ALL SELECT 'Triggers', COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = DATABASE()
UNION ALL SELECT 'Stored Functions', COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_TYPE = 'FUNCTION'
UNION ALL SELECT 'Stored Procedures', COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = DATABASE() AND ROUTINE_TYPE = 'PROCEDURE'""",
  [
      {"line": "SELECT 'Base Tables' ... WHERE TABLE_TYPE = 'BASE TABLE'", "text": "Counts all real persistent relational tables."},
      {"line": "UNION ALL SELECT 'Views' ...", "text": "Appends count of virtual database views."},
      {"line": "UNION ALL SELECT 'Foreign Keys' ...", "text": "Reads referential integrity constraints from catalog."},
      {"line": "UNION ALL SELECT 'Triggers' ...", "text": "Counts event-driven stored triggers."},
      {"line": "UNION ALL SELECT 'Stored Functions' / 'Procedures' ...", "text": "Counts compiled stored routines in the catalog."}
  ],
  ["information_schema"])

q("db_tables_summary", "Table Storage & Row Counts", "Storage Engine",
  "Inspects InnoDB storage engine details, physical row estimates, and collation for all 8 project tables.",
  """SELECT TABLE_NAME, ENGINE, TABLE_ROWS, DATA_LENGTH, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME""",
  [
      {"line": "SELECT TABLE_NAME, ENGINE, TABLE_ROWS ...", "text": "Projects table name, storage engine, row estimates, and byte length."},
      {"line": "FROM information_schema.TABLES", "text": "Accesses MySQL's internal metadata dictionary."},
      {"line": "WHERE TABLE_SCHEMA = DATABASE()", "text": "Restricts inspection strictly to the active schema."},
      {"line": "AND TABLE_TYPE = 'BASE TABLE'", "text": "Excludes database views to focus on base storage tables."}
  ],
  ["information_schema"])

# 2. Constraints
q("constraints_list", "All Constraints (PK, UK, FK)", "Constraints",
  "Lists all integrity constraints declared across all 8 tables from the database catalog.",
  """SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = DATABASE()
ORDER BY TABLE_NAME, CONSTRAINT_TYPE, CONSTRAINT_NAME""",
  [
      {"line": "SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE", "text": "Selects the target table, constraint identifier, and constraint rule."},
      {"line": "FROM information_schema.TABLE_CONSTRAINTS", "text": "Queries all active constraints stored by MySQL."},
      {"line": "WHERE CONSTRAINT_SCHEMA = DATABASE()", "text": "Filters to api_management database."},
      {"line": "ORDER BY TABLE_NAME, CONSTRAINT_TYPE", "text": "Sorts by table and groups constraint types together."}
  ],
  ["information_schema"])

# 3. Keys
q("fk_list", "Foreign Key Catalog & Referential Rules", "Relationships",
  "Lists every FOREIGN KEY in the schema with its ON UPDATE and ON DELETE rules from the MySQL catalog.",
  """SELECT kcu.TABLE_NAME AS child_table, kcu.COLUMN_NAME AS child_column,
       kcu.REFERENCED_TABLE_NAME AS parent_table, kcu.REFERENCED_COLUMN_NAME AS parent_column,
       kcu.CONSTRAINT_NAME, rc.UPDATE_RULE, rc.DELETE_RULE
FROM information_schema.KEY_COLUMN_USAGE kcu
JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
 AND rc.TABLE_NAME = kcu.TABLE_NAME
 AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
WHERE kcu.TABLE_SCHEMA = DATABASE() AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION""",
  [
      {"line": "SELECT kcu.TABLE_NAME AS child_table ...", "text": "Identifies child column linking to parent referenced column."},
      {"line": "FROM information_schema.KEY_COLUMN_USAGE kcu", "text": "Reads column-level key mapping."},
      {"line": "JOIN information_schema.REFERENTIAL_CONSTRAINTS rc", "text": "Joins to referential rules catalog to read cascade behavior."},
      {"line": "WHERE kcu.REFERENCED_TABLE_NAME IS NOT NULL", "text": "Filters out Primary Keys to isolate Foreign Keys."},
      {"line": "ORDER BY kcu.TABLE_NAME ...", "text": "Sorts child tables and composite keys in ordinal order."}
  ],
  ["ROLE", "TEAM", "USER", "API", "API_VERSION", "ENDPOINT", "SUBSCRIPTION", "PERMISSION"])

# 6. Basic SELECT
q("select_filter_apis", "SELECT with WHERE, Sorting & Limit", "SELECT",
  "Demonstrates relational projection, selection predicate (WHERE), column aliasing, and sorting.",
  """SELECT api_id, api_name, category, status, DATE(created_at) AS created_on
FROM API
WHERE status = 'ACTIVE'
ORDER BY api_name ASC""",
  [
      {"line": "SELECT api_id, api_name, category, status, DATE(created_at) AS created_on", "text": "Projects specific columns and applies DATE() scalar function."},
      {"line": "FROM API", "text": "Specifies the primary API entity table."},
      {"line": "WHERE status = 'ACTIVE'", "text": "Selection predicate: filters row set to active APIs only."},
      {"line": "ORDER BY api_name ASC", "text": "Sorts returned records alphabetically by API title."}
  ],
  ["API"])

q("select_pattern_matching", "Pattern Matching with LIKE Operator", "SELECT",
  "Uses SQL wildcard pattern matching with LIKE to search textual descriptions.",
  """SELECT api_id, api_name, category, description
FROM API
WHERE description LIKE '%service%' OR description LIKE '%payment%'
ORDER BY api_id""",
  [
      {"line": "SELECT api_id, api_name, category, description", "text": "Selects descriptive attributes of the API."},
      {"line": "FROM API", "text": "Specifies API table."},
      {"line": "WHERE description LIKE '%service%' OR description LIKE '%payment%'", "text": "Pattern matching: % matches any sequence of zero or more characters."},
      {"line": "ORDER BY api_id", "text": "Sorts result set by primary key."}
  ],
  ["API"])

q("select_range_dates", "Range Filtering with BETWEEN and CURDATE()", "SELECT",
  "Filters subscriptions created within a calendar date range using BETWEEN and current date.",
  """SELECT subscription_id, api_id, consumer_id, status, subscribe_date, expires_at
FROM SUBSCRIPTION
WHERE subscribe_date BETWEEN '2026-01-01' AND CURDATE()
ORDER BY subscribe_date DESC""",
  [
      {"line": "SELECT subscription_id, api_id, consumer_id ...", "text": "Projects key subscription attributes."},
      {"line": "FROM SUBSCRIPTION", "text": "Specifies SUBSCRIPTION entity table."},
      {"line": "WHERE subscribe_date BETWEEN '2026-01-01' AND CURDATE()", "text": "Inclusive range filter between Jan 1, 2026 and current system date."},
      {"line": "ORDER BY subscribe_date DESC", "text": "Orders newest subscriptions first."}
  ],
  ["SUBSCRIPTION"])

# 7. JOINs
q("inner_api_owner", "INNER JOIN - API with its Owner", "INNER JOIN",
  "INNER JOIN returns only rows that have matching keys in BOTH tables: each API matched with the user who created it.",
  """SELECT A.api_id, A.api_name, U.full_name AS owner_name, A.category, A.status
FROM API A
INNER JOIN `USER` U ON A.owner_id = U.user_id
ORDER BY A.api_id""",
  [
      {"line": "SELECT A.api_id, A.api_name, U.full_name ...", "text": "Projects attributes from both API (A) and USER (U) tables."},
      {"line": "FROM API A", "text": "Left table aliased as A."},
      {"line": "INNER JOIN `USER` U ON A.owner_id = U.user_id", "text": "Joins USER on foreign key owner_id = primary key user_id."},
      {"line": "ORDER BY A.api_id", "text": "Orders result set by API identifier."}
  ],
  ["API", "USER"])

q("inner_subscription", "INNER JOIN (4 Tables) - Subscription Details", "INNER JOIN",
  "Joins SUBSCRIPTION with USER, API, and API_VERSION. The version join utilizes composite keys (version_id AND api_id).",
  """SELECT S.subscription_id, U.full_name AS consumer, A.api_name, V.version_number,
       S.status, S.subscribe_date, S.expires_at
FROM SUBSCRIPTION S
INNER JOIN `USER` U ON S.consumer_id = U.user_id
INNER JOIN API A ON S.api_id = A.api_id
INNER JOIN API_VERSION V ON S.version_id = V.version_id AND S.api_id = V.api_id
ORDER BY S.subscription_id""",
  [
      {"line": "SELECT S.subscription_id, U.full_name ...", "text": "Projects consumer name, API name, version number, and subscription dates."},
      {"line": "FROM SUBSCRIPTION S", "text": "Central subscription entity table."},
      {"line": "INNER JOIN `USER` U ON S.consumer_id = U.user_id", "text": "Resolves consumer identity."},
      {"line": "INNER JOIN API A ON S.api_id = A.api_id", "text": "Resolves target API details."},
      {"line": "INNER JOIN API_VERSION V ON S.version_id = V.version_id AND S.api_id = V.api_id", "text": "Composite FK join: guarantees version belongs to that exact API."},
      {"line": "ORDER BY S.subscription_id", "text": "Sorts sequentially by subscription ID."}
  ],
  ["SUBSCRIPTION", "USER", "API", "API_VERSION"])

q("left_versions", "LEFT JOIN - Versions per API (Preserving Unmatched)", "LEFT JOIN",
  "LEFT JOIN preserves all rows from the left table (API) even if no matching rows exist in the right table (API_VERSION).",
  """SELECT A.api_name, COUNT(V.version_id) AS total_versions
FROM API A
LEFT JOIN API_VERSION V ON A.api_id = V.api_id
GROUP BY A.api_id, A.api_name
ORDER BY A.api_id""",
  [
      {"line": "SELECT A.api_name, COUNT(V.version_id) ...", "text": "Counts non-null version IDs per API."},
      {"line": "FROM API A", "text": "Left table: every API is preserved."},
      {"line": "LEFT JOIN API_VERSION V ON A.api_id = V.api_id", "text": "Right table match; unmatched APIs will produce NULL for version_id."},
      {"line": "GROUP BY A.api_id, A.api_name", "text": "Groups rows by unique API."},
      {"line": "ORDER BY A.api_id", "text": "Sorts by API ID."}
  ],
  ["API", "API_VERSION"])

q("left_users_subs", "LEFT JOIN - User Subscriptions Count", "LEFT JOIN",
  "Admins and developers do not subscribe, yet they still appear with count 0 because of the LEFT JOIN. An INNER JOIN would omit them.",
  """SELECT U.full_name, R.role_name, COUNT(S.subscription_id) AS subscriptions
FROM `USER` U
INNER JOIN `ROLE` R ON U.role_id = R.role_id
LEFT JOIN SUBSCRIPTION S ON S.consumer_id = U.user_id
GROUP BY U.user_id, U.full_name, R.role_name
ORDER BY subscriptions DESC, U.full_name ASC""",
  [
      {"line": "SELECT U.full_name, R.role_name, COUNT(S.subscription_id) ...", "text": "Counts subscriptions for each user."},
      {"line": "FROM `USER` U INNER JOIN `ROLE` R ON U.role_id = R.role_id", "text": "Joins role to identify Admin, Developer, and Consumer."},
      {"line": "LEFT JOIN SUBSCRIPTION S ON S.consumer_id = U.user_id", "text": "Keeps all users regardless of whether they have subscribed."},
      {"line": "GROUP BY U.user_id, U.full_name, R.role_name", "text": "Aggregates per user."},
      {"line": "ORDER BY subscriptions DESC, U.full_name ASC", "text": "Displays highest subscribers first."}
  ],
  ["USER", "ROLE", "SUBSCRIPTION"])

# 8. Aggregates
q("agg_all", "COUNT, SUM, AVG, MAX, MIN on Subscriptions", "Aggregates",
  "Applies 5 SQL aggregate functions over the SUBSCRIPTION table. Uses project's stored function subscription_days().",
  """SELECT COUNT(*) AS total_subscriptions,
       SUM(subscription_days(subscribe_date, expires_at)) AS total_subscribed_days,
       AVG(subscription_days(subscribe_date, expires_at)) AS avg_duration_days,
       MAX(expires_at) AS latest_expiry,
       MIN(subscribe_date) AS earliest_subscription
FROM SUBSCRIPTION""",
  [
      {"line": "SELECT COUNT(*) AS total_subscriptions", "text": "Calculates total number of subscription records."},
      {"line": "SUM(subscription_days(subscribe_date, expires_at))", "text": "Sums the total days computed by stored function subscription_days()."},
      {"line": "AVG(subscription_days(subscribe_date, expires_at))", "text": "Computes arithmetic mean subscription duration in days."},
      {"line": "MAX(expires_at) AS latest_expiry", "text": "Finds the latest expiration date in the table."},
      {"line": "MIN(subscribe_date) AS earliest_subscription", "text": "Finds the earliest subscription start date in the table."},
      {"line": "FROM SUBSCRIPTION", "text": "Table over which the aggregates are evaluated."}
  ],
  ["SUBSCRIPTION"])

q("agg_api", "COUNT, Conditional SUM, MIN, MAX on API", "Aggregates",
  "Demonstrates conditional aggregation using boolean expressions inside SUM() and average key calculation.",
  """SELECT COUNT(*) AS total_apis,
       SUM(status = 'ACTIVE') AS active_apis,
       AVG(api_id) AS average_api_id,
       MIN(created_at) AS first_api_created,
       MAX(created_at) AS latest_api_created
FROM API""",
  [
      {"line": "SELECT COUNT(*) AS total_apis", "text": "Calculates total APIs registered in the system."},
      {"line": "SUM(status = 'ACTIVE') AS active_apis", "text": "Conditional aggregate: boolean status='ACTIVE' evaluates to 1 or 0."},
      {"line": "AVG(api_id) AS average_api_id", "text": "Computes arithmetic average of primary key values."},
      {"line": "MIN(created_at) / MAX(created_at)", "text": "Finds earliest and most recent creation timestamps."}
  ],
  ["API"])

# 9. GROUP BY and HAVING
q("group_by", "GROUP BY - Subscriptions and Duration per API", "GROUP BY",
  "GROUP BY collapses individual rows into groups based on API, computing aggregates per group.",
  """SELECT A.api_name,
       COUNT(S.subscription_id) AS total_subscriptions,
       COALESCE(SUM(subscription_days(S.subscribe_date, S.expires_at)), 0) AS total_days
FROM API A
LEFT JOIN SUBSCRIPTION S ON A.api_id = S.api_id
GROUP BY A.api_id, A.api_name
ORDER BY total_subscriptions DESC, A.api_name ASC""",
  [
      {"line": "SELECT A.api_name, COUNT(S.subscription_id) ...", "text": "Projects API details and aggregate counts."},
      {"line": "FROM API A LEFT JOIN SUBSCRIPTION S ON A.api_id = S.api_id", "text": "Left joins subscriptions to retain APIs with zero subscriptions."},
      {"line": "GROUP BY A.api_id, A.api_name", "text": "Groups rows by API ID and name."},
      {"line": "ORDER BY total_subscriptions DESC", "text": "Ranks APIs by popularity."}
  ],
  ["API", "SUBSCRIPTION"])

q("having", "HAVING Clause - APIs with Multiple Subscriptions", "HAVING",
  "WHERE filters rows BEFORE grouping; HAVING filters groups AFTER aggregation.",
  """SELECT A.api_name, COUNT(S.subscription_id) AS total_subscriptions
FROM API A
JOIN SUBSCRIPTION S ON A.api_id = S.api_id
GROUP BY A.api_id, A.api_name
HAVING COUNT(S.subscription_id) > 1""",
  [
      {"line": "SELECT A.api_name, COUNT(S.subscription_id) AS total_subscriptions", "text": "Computes subscription count per API."},
      {"line": "FROM API A JOIN SUBSCRIPTION S ON A.api_id = S.api_id", "text": "Joins API and SUBSCRIPTION."},
      {"line": "GROUP BY A.api_id, A.api_name", "text": "Groups rows by API."},
      {"line": "HAVING COUNT(S.subscription_id) > 1", "text": "Group filter: excludes any API group with 1 or fewer subscriptions."}
  ],
  ["API", "SUBSCRIPTION"])

q("team_having", "GROUP BY + HAVING - Teams with Multiple Members", "HAVING",
  "Filters aggregated teams to show only those containing more than one registered user.",
  """SELECT T.team_name, COUNT(U.user_id) AS members
FROM TEAM T
JOIN `USER` U ON U.team_id = T.team_id
GROUP BY T.team_id, T.team_name
HAVING COUNT(U.user_id) > 1""",
  [
      {"line": "SELECT T.team_name, COUNT(U.user_id) AS members", "text": "Counts members per team."},
      {"line": "FROM TEAM T JOIN `USER` U ON U.team_id = T.team_id", "text": "Joins team and user entities."},
      {"line": "GROUP BY T.team_id, T.team_name", "text": "Collapses into one row per team."},
      {"line": "HAVING COUNT(U.user_id) > 1", "text": "Discards single-member or empty teams from the output."}
  ],
  ["TEAM", "USER"])

# 10. Subqueries
q("sub_in", "Subquery with IN Operator", "Subquery",
  "The inner query returns a list of subscribed API IDs; the outer query keeps APIs whose ID is in that list.",
  """SELECT api_name
FROM API
WHERE api_id IN (SELECT api_id FROM SUBSCRIPTION)
ORDER BY api_name""",
  [
      {"line": "SELECT api_name FROM API", "text": "Outer query: selects API records."},
      {"line": "WHERE api_id IN (", "text": "Membership predicate checking if ID exists in subquery result."},
      {"line": "    SELECT api_id FROM SUBSCRIPTION", "text": "Inner subquery: evaluates dynamically to return subscribed API IDs."},
      {"line": ") ORDER BY api_name", "text": "Closes subquery and sorts results."}
  ],
  ["API", "SUBSCRIPTION"])

q("sub_not_exists", "Correlated Subquery with NOT EXISTS", "Subquery",
  "The inner query references the outer row (S.api_id = A.api_id), executing once per candidate row. NULL-safe.",
  """SELECT A.api_name
FROM API A
WHERE NOT EXISTS (
    SELECT 1 FROM SUBSCRIPTION S WHERE S.api_id = A.api_id
)""",
  [
      {"line": "SELECT A.api_name FROM API A", "text": "Outer query examining each API row."},
      {"line": "WHERE NOT EXISTS (", "text": "Returns TRUE if the subquery returns 0 rows."},
      {"line": "    SELECT 1 FROM SUBSCRIPTION S WHERE S.api_id = A.api_id", "text": "Correlated condition: references outer row A.api_id."},
      {"line": ")", "text": "Safe against NULLs in SUBSCRIPTION."}
  ],
  ["API", "SUBSCRIPTION"])

q("sub_scalar", "Scalar Subquery in SELECT Clause", "Subquery",
  "A subquery returning exactly one value per outer row, used directly as a projected column.",
  """SELECT A.api_name,
       (SELECT MAX(V.release_date) FROM API_VERSION V WHERE V.api_id = A.api_id) AS latest_version_date
FROM API A
ORDER BY A.api_name""",
  [
      {"line": "SELECT A.api_name,", "text": "Projects API name from outer query."},
      {"line": "    (SELECT MAX(V.release_date) FROM API_VERSION V WHERE V.api_id = A.api_id) AS latest_version_date", "text": "Scalar subquery returning single max release date for the candidate API."},
      {"line": "FROM API A ORDER BY A.api_name", "text": "Specifies candidate outer table."}
  ],
  ["API", "API_VERSION"])

q("sub_derived", "Derived Table in HAVING - Most Subscribed API", "Subquery",
  "The inner derived table calculates subscription counts; MAX() extracts the maximum, and HAVING retains the leader.",
  """SELECT A.api_name, COUNT(*) AS total_subscriptions
FROM API A
JOIN SUBSCRIPTION S ON S.api_id = A.api_id
GROUP BY A.api_id, A.api_name
HAVING COUNT(*) = (
    SELECT MAX(c) FROM (SELECT COUNT(*) AS c FROM SUBSCRIPTION GROUP BY api_id) AS sub_counts
)""",
  [
      {"line": "SELECT A.api_name, COUNT(*) AS total_subscriptions", "text": "Calculates subscriptions for outer API groups."},
      {"line": "FROM API A JOIN SUBSCRIPTION S ON S.api_id = A.api_id GROUP BY ...", "text": "Groups subscriptions by API."},
      {"line": "HAVING COUNT(*) = (", "text": "Keeps groups equal to the subquery peak value."},
      {"line": "    SELECT MAX(c) FROM (SELECT COUNT(*) AS c FROM SUBSCRIPTION GROUP BY api_id) AS sub_counts", "text": "Derived table subquery finding the highest count across all APIs."},
      {"line": ")", "text": "Completes evaluation."}
  ],
  ["API", "SUBSCRIPTION"])

# 11. Views
q("view_api_details", "SELECT * FROM api_details_view", "View",
  "Reads from the database VIEW api_details_view (encapsulates API JOIN USER).",
  """SELECT * FROM api_details_view""",
  [
      {"line": "SELECT *", "text": "Retrieves all pre-joined columns defined in the view."},
      {"line": "FROM api_details_view", "text": "Virtual table stored in the MySQL catalog."}
  ],
  ["api_details_view"])

q("view_api_version", "SELECT * FROM api_version_view", "View",
  "Reads from the database VIEW api_version_view (encapsulates API JOIN API_VERSION).",
  """SELECT * FROM api_version_view""",
  [
      {"line": "SELECT *", "text": "Retrieves API name, version numbers, status, and release dates."},
      {"line": "FROM api_version_view", "text": "Virtual view stored in MySQL."}
  ],
  ["api_version_view"])

q("view_subscription", "SELECT * FROM subscription_details_view", "View",
  "Reads from the database VIEW subscription_details_view (joins SUBSCRIPTION, USER, API, API_VERSION).",
  """SELECT * FROM subscription_details_view""",
  [
      {"line": "SELECT *", "text": "Projects resolved consumer name, API name, version, and validity."},
      {"line": "FROM subscription_details_view", "text": "4-table join encapsulated directly in MySQL catalog."}
  ],
  ["subscription_details_view"])

q("view_filtered", "Querying a View with WHERE Predicates", "View",
  "Demonstrates that a database view can be filtered and ordered exactly like a physical table.",
  """SELECT api_name, version_number, release_date
FROM api_version_view
WHERE status = 'ACTIVE'
ORDER BY api_name, version_number""",
  [
      {"line": "SELECT api_name, version_number, release_date", "text": "Selects projected view columns."},
      {"line": "FROM api_version_view", "text": "Specifies view as data source."},
      {"line": "WHERE status = 'ACTIVE'", "text": "Pushes selection filter into the view definition inside MySQL."},
      {"line": "ORDER BY api_name, version_number", "text": "Orders result set."}
  ],
  ["api_version_view"])

# 14. Triggers
q("trigger_list", "Triggers Stored in MySQL Catalog", "Trigger",
  "Queries MySQL's information_schema to prove the physical existence of triggers and their firing events.",
  """SELECT TRIGGER_NAME, EVENT_MANIPULATION AS event, EVENT_OBJECT_TABLE AS on_table, ACTION_TIMING AS timing
FROM information_schema.TRIGGERS
WHERE TRIGGER_SCHEMA = DATABASE()
ORDER BY TRIGGER_NAME""",
  [
      {"line": "SELECT TRIGGER_NAME, EVENT_MANIPULATION ...", "text": "Extracts trigger name, event (INSERT/UPDATE/DELETE), target table, and timing (BEFORE/AFTER)."},
      {"line": "FROM information_schema.TRIGGERS", "text": "MySQL's trigger metadata catalog."},
      {"line": "WHERE TRIGGER_SCHEMA = DATABASE()", "text": "Restricts to active schema."},
      {"line": "ORDER BY TRIGGER_NAME", "text": "Sorts alphabetically."}
  ],
  ["information_schema"])

REPORT_ORDER = [
    "view_api_details", "view_api_version", "view_subscription",
    "inner_api_owner", "inner_subscription", "left_versions", "left_users_subs",
    "group_by", "having", "sub_in", "sub_not_exists", "sub_scalar", "sub_derived",
    "agg_all", "agg_api"
]

# --------------------------------------------------------------------------
# Step Runner Helper
# --------------------------------------------------------------------------
def step(cur, label, sql, args=None, note=None):
    shown = cur.mogrify(sql, args) if args is not None else sql
    d = dict(
        label=label,
        sql=shown.strip(),
        note=note,
        columns=[],
        rows=[],
        rowcount=None,
        error=None,
        lastrowid=None,
    )
    try:
        cur.execute(sql, args)
        d["lastrowid"] = cur.lastrowid
        d["rowcount"] = cur.rowcount
        if cur.description:
            d["columns"] = [c[0] for c in cur.description]
            d["rows"] = clean_rows(cur.fetchall())
        while cur.nextset():
            pass
    except pymysql.MySQLError as e:
        d["error"] = f"MySQL error {e.args[0]}: {e.args[1]}"
    return d


def info(label, note):
    return dict(label=label, sql="", note=note, columns=[], rows=[], rowcount=None, error=None, lastrowid=None)


def _tx(cur, fn):
    """Run fn inside a transaction that is always rolled back."""
    cur.execute("START TRANSACTION")
    try:
        return fn()
    finally:
        cur.execute("ROLLBACK")
        cur.execute("SET SESSION TIMESTAMP = DEFAULT")


def _int(p, name):
    try:
        return int(p.get(name))
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a whole number")


def _date(p, name):
    try:
        return datetime.date.fromisoformat(str(p.get(name)))
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a valid date (YYYY-MM-DD)")


# --------------------------------------------------------------------------
# Interactive Demonstration Handlers
# --------------------------------------------------------------------------
def d_table(cur, conn, p):
    name = p.get("table")
    if name not in TABLES:
        raise ValueError("unknown table")
    return [step(cur, f"Table {name}", TABLES[name])]


def d_show_create(cur, conn, p):
    name = p.get("table")
    if name not in TABLES:
        raise ValueError("unknown table")
    return [step(cur, f"DDL of table {name}", f"SHOW CREATE TABLE `{name}`")]


def d_unique_violation(cur, conn, p):
    def run():
        s = [info("What this proves", "UNIQUE constraints make MySQL reject duplicate values. The statement below attempts to insert an already registered email. It is expected to FAIL with Error 1062.")]
        s.append(step(cur, "Attempt duplicate email insertion in USER table",
                      "INSERT INTO `USER` (full_name, email, password_hash, role_id, team_id) VALUES ('Duplicate User', 'arjun@company.com', 'dummy_hash', 2, 2)",
                      note="Expected Error: 1062 (Duplicate entry 'arjun@company.com' for key 'user.uq_user_email')"))
        s.append(step(cur, "Verification: Row count in USER unchanged", "SELECT COUNT(*) AS total_users FROM `USER`"))
        return s
    return _tx(cur, run)


def d_not_null_violation(cur, conn, p):
    def run():
        s = [info("What this proves", "NOT NULL constraints enforce mandatory fields at database engine level. Inserting NULL into api_name must fail.")]
        s.append(step(cur, "Attempt NULL insert into API.api_name",
                      "INSERT INTO API (api_name, description, category, status, owner_id) VALUES (NULL, 'Missing title', 'Test', 'ACTIVE', 1)",
                      note="Expected Error: 1048 (Column 'api_name' cannot be null)"))
        s.append(step(cur, "Verification: Row count in API unchanged", "SELECT COUNT(*) AS total_apis FROM API"))
        return s
    return _tx(cur, run)


def d_fk_demo(cur, conn, p):
    def run():
        s = [info("What this proves", "Foreign keys make MySQL guarantee referential integrity. All 3 statements below violate relational rules and are rejected by MySQL.")]
        s.append(step(cur, "1) INSERT API with non-existent owner (expect Error 1452)",
                      "INSERT INTO API (api_name, owner_id) VALUES ('FK test API', 9999)"))
        s.append(step(cur, "2) DELETE user who still owns APIs - ON DELETE RESTRICT (expect Error 1451)",
                      "DELETE FROM `USER` WHERE user_id = 2"))
        s.append(step(cur, "3) Composite FK: Subscribe to API 1 using version of API 2 (expect Error 1452)",
                      "INSERT INTO SUBSCRIPTION (api_id, version_id, consumer_id, subscribe_date) VALUES (1, 3, 4, CURDATE())"))
        s.append(step(cur, "Verification: Row counts completely unchanged",
                      "SELECT (SELECT COUNT(*) FROM API) AS apis, (SELECT COUNT(*) FROM `USER`) AS users, (SELECT COUNT(*) FROM SUBSCRIPTION) AS subscriptions"))
        return s
    return _tx(cur, run)


def d_fk_cascade(cur, conn, p):
    def run():
        s = [info("What this proves", "CASCADE rules: Deleting an API automatically deletes its child API_VERSION and ENDPOINT rows without orphan records.")]
        s.append(step(cur, "Setup: Insert temporary API",
                      "INSERT INTO API (api_name, description, category, status, owner_id) VALUES ('CASCADE_TEST_API', 'Temp test', 'Test', 'ACTIVE', 1)"))
        aid = s[-1]["lastrowid"]
        s.append(step(cur, "Setup: Insert child version",
                      "INSERT INTO API_VERSION (api_id, version_number, release_date) VALUES (%s, 'v99', CURDATE())", (aid,)))
        vid = s[-1]["lastrowid"]
        s.append(step(cur, "Setup: Insert grandchild endpoint",
                      "INSERT INTO ENDPOINT (version_id, method, endpoint_path) VALUES (%s, 'GET', '/test-cascade')", (vid,)))
        eid = s[-1]["lastrowid"]
        s.append(step(cur, "BEFORE DELETE: Verifying existence of child records",
                      "SELECT (SELECT COUNT(*) FROM API WHERE api_id=%s) AS api_exists, "
                      "(SELECT COUNT(*) FROM API_VERSION WHERE version_id=%s) AS version_exists, "
                      "(SELECT COUNT(*) FROM ENDPOINT WHERE endpoint_id=%s) AS endpoint_exists", (aid, vid, eid)))
        s.append(step(cur, "ACTION: DELETE parent API", "DELETE FROM API WHERE api_id = %s", (aid,),
                      note="ON DELETE CASCADE on API_VERSION and ENDPOINT automatically propagates."))
        s.append(step(cur, "AFTER DELETE: Proving child and grandchild records were automatically cascaded",
                      "SELECT (SELECT COUNT(*) FROM API WHERE api_id=%s) AS api_exists, "
                      "(SELECT COUNT(*) FROM API_VERSION WHERE version_id=%s) AS version_exists, "
                      "(SELECT COUNT(*) FROM ENDPOINT WHERE endpoint_id=%s) AS endpoint_exists", (aid, vid, eid)))
        s.append(info("Clean-up", "Transaction rolled back: seed database untouched."))
        return s
    return _tx(cur, run)


def d_ddl(cur, conn, p):
    steps = []
    cur.execute("DROP TABLE IF EXISTS demo_ddl_test")
    try:
        steps.append(step(cur, "1. CREATE TABLE",
                          "CREATE TABLE demo_ddl_test (id INT PRIMARY KEY AUTO_INCREMENT, label VARCHAR(50) NOT NULL) ENGINE=InnoDB",
                          note="A disposable demonstration table. Project tables are not altered."))
        steps.append(step(cur, "DESCRIBE (after CREATE)", "DESCRIBE demo_ddl_test"))
        steps.append(step(cur, "2. ALTER TABLE ... ADD COLUMN",
                          "ALTER TABLE demo_ddl_test ADD COLUMN created_on DATE NULL"))
        steps.append(step(cur, "DESCRIBE (after ALTER ADD)", "DESCRIBE demo_ddl_test"))
        steps.append(step(cur, "3. ALTER TABLE ... DROP COLUMN",
                          "ALTER TABLE demo_ddl_test DROP COLUMN created_on"))
        steps.append(step(cur, "DESCRIBE (after ALTER DROP)", "DESCRIBE demo_ddl_test"))
    finally:
        steps.append(step(cur, "4. DROP TABLE (clean-up)", "DROP TABLE IF EXISTS demo_ddl_test"))
    steps.append(step(cur, "Verification: Table successfully removed",
                      "SELECT COUNT(*) AS demo_tables_left FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'demo_ddl_test'"))
    return steps


def d_dml(cur, conn, p):
    steps = []
    name = "Demo Team (temp)"
    cur.execute("DELETE FROM TEAM WHERE team_name = %s", (name,))
    sel = "SELECT team_id, team_name, description FROM TEAM ORDER BY team_id"
    steps.append(step(cur, "1. BEFORE: TEAM table state", sel))
    steps.append(step(cur, "2. INSERT statement",
                      "INSERT INTO TEAM (team_name, description) VALUES (%s, %s)",
                      (name, "Temporary demonstration team")))
    steps.append(step(cur, "SELECT after INSERT", sel))
    steps.append(step(cur, "3. UPDATE statement",
                      "UPDATE TEAM SET description = %s WHERE team_name = %s",
                      ("Updated demo description", name)))
    steps.append(step(cur, "SELECT after UPDATE",
                      "SELECT team_id, team_name, description FROM TEAM WHERE team_name = %s", (name,)))
    steps.append(step(cur, "4. DELETE statement",
                      "DELETE FROM TEAM WHERE team_name = %s", (name,)))
    steps.append(step(cur, "5. AFTER: TEAM restored to original records", sel))
    return steps


def d_dml_rollback(cur, conn, p):
    def run():
        s = []
        name = "Atomicity Team"
        s.append(step(cur, "1. START TRANSACTION", "START TRANSACTION"))
        s.append(step(cur, "2. INSERT test record inside transaction",
                      "INSERT INTO TEAM (team_name, description) VALUES (%s, 'Will be rolled back')", (name,)))
        s.append(step(cur, "3. Query within transaction: Record is visible",
                      "SELECT team_id, team_name, description FROM TEAM WHERE team_name = %s", (name,)))
        s.append(step(cur, "4. Issue ROLLBACK", "ROLLBACK"))
        cur.execute("ROLLBACK")
        s.append(step(cur, "5. Query after ROLLBACK: Record was completely undone",
                      "SELECT team_id, team_name, description FROM TEAM WHERE team_name = %s", (name,)))
        return s
    return run()


def d_trigger_api(cur, conn, p):
    def run():
        s = []
        s.append(step(cur, "Setup: Create disposable test API",
                      "INSERT INTO API (api_name, description, category, status, owner_id) "
                      "VALUES ('TRIGGER_DEMO_API', 'Temporary trigger demo', 'Demo', 'ACTIVE', 1)"))
        api_id = s[-1]["lastrowid"]
        for ver, st, dep in (("v1", "ACTIVE", None), ("v2", "ACTIVE", None), ("v0", "DEPRECATED", "2025-01-01")):
            s.append(step(cur, f"Setup: Add version {ver} ({st})",
                          "INSERT INTO API_VERSION (api_id, version_number, release_date, status, deprecated_date) "
                          "VALUES (%s, %s, '2025-01-01', %s, %s)", (api_id, ver, st, dep)))
        ver_sql = ("SELECT version_id, version_number, status, deprecated_date FROM API_VERSION "
                   "WHERE api_id = %s ORDER BY version_id")
        s.append(step(cur, "BEFORE - Version records of test API", ver_sql, (api_id,)))
        s.append(step(cur, "ACTION - Deprecate the API (This is the ONLY statement Python executes)",
                      "UPDATE API SET status = 'DEPRECATED' WHERE api_id = %s", (api_id,),
                      note="MySQL Trigger after_api_deprecated fires automatically inside database engine."))
        s.append(step(cur, "AFTER - Version records (v1, v2 changed to DEPRECATED by TRIGGER; v0 kept old date)",
                      ver_sql, (api_id,)))
        s.append(info("Clean-up", "Transaction rolled back: demo API and versions discarded."))
        return s
    return _tx(cur, run)


def d_trigger_sub(cur, conn, p):
    def run():
        s = []
        ins = ("INSERT INTO SUBSCRIPTION (api_id, version_id, consumer_id, status, subscribe_date, expires_at) "
               "VALUES (1, 2, 4, 'ACTIVE', CURDATE() - INTERVAL 30 DAY, CURDATE() - INTERVAL 1 DAY)")
        ins2 = ("INSERT INTO SUBSCRIPTION (api_id, version_id, consumer_id, status, subscribe_date, expires_at) "
                "VALUES (1, 2, 4, 'ACTIVE', CURDATE(), CURDATE() + INTERVAL 30 DAY)")
        sel = "SELECT subscription_id, status, subscribe_date, expires_at FROM SUBSCRIPTION WHERE subscription_id = %s"
        s.append(step(cur, "A) INSERT ACTIVE subscription with past expiry date", ins,
                      note="Trigger check_subscription_expiry_insert (BEFORE INSERT) intercepts and sets status to EXPIRED."))
        a = s[-1]["lastrowid"]
        s.append(step(cur, "A) Result: Status automatically stored as EXPIRED", sel, (a,)))
        s.append(step(cur, "B) INSERT ACTIVE subscription expiring in 30 days", ins2,
                      note="Valid future expiry: trigger leaves it ACTIVE."))
        b = s[-1]["lastrowid"]
        s.append(step(cur, "B) Result: Stays ACTIVE", sel, (b,)))
        s.append(step(cur, "C) UPDATE subscription B to past expiry with status explicitly chosen 'ACTIVE'",
                      "UPDATE SUBSCRIPTION SET expires_at = CURDATE() - INTERVAL 1 DAY, status = 'ACTIVE' WHERE subscription_id = %s", (b,),
                      note="Trigger check_subscription_expiry (BEFORE UPDATE) overrides choice to EXPIRED."))
        s.append(step(cur, "C) Result: Overridden to EXPIRED by MySQL trigger", sel, (b,)))
        s.append(info("Clean-up", "Transaction rolled back: test subscriptions discarded."))
        return s
    return _tx(cur, run)


def d_trigger_sweep(cur, conn, p):
    day = _date(p, "sim_date")

    def run():
        s = []
        s.append(step(cur, "1. Advance this connection session clock to simulated date",
                      "SET SESSION TIMESTAMP = UNIX_TIMESTAMP(%s)", (f"{day} 12:00:00",),
                      note="Only this connection sees the simulated date. Session clock resets on rollback."))
        s.append(step(cur, "2. Verify CURDATE() as MySQL now perceives it", "SELECT CURDATE() AS simulated_today"))
        sel = "SELECT subscription_id, status, expires_at FROM SUBSCRIPTION ORDER BY subscription_id"
        s.append(step(cur, "3. BEFORE: Current subscription statuses", sel))
        s.append(step(cur, "4. ACTION: Expiry sweep (no-op UPDATE triggering BEFORE UPDATE on every row)",
                      "UPDATE SUBSCRIPTION SET expires_at = expires_at WHERE status = 'ACTIVE' AND expires_at < CURDATE()",
                      note="Python does not evaluate logic: trigger check_subscription_expiry marks overdue rows EXPIRED."))
        s.append(step(cur, "5. AFTER: Subscription statuses evaluated by trigger", sel))
        s.append(info("Clean-up", "Transaction rolled back and connection timestamp restored."))
        return s
    out = _tx(cur, run)
    out.append(step(cur, "Verification: Real system date and production records intact",
                    "SELECT CURDATE() AS real_today, (SELECT COUNT(*) FROM SUBSCRIPTION WHERE status = 'EXPIRED') AS expired_rows"))
    return out


def d_fn_age(cur, conn, p):
    day = _date(p, "api_date")
    return [
        step(cur, "api_age(api_date) - Evaluated inside MySQL",
             "SELECT api_age(%s) AS calculated_age_years, CURDATE() AS evaluated_on_date", (str(day),)),
        step(cur, "api_age() applied across all registered APIs",
             "SELECT api_id, api_name, created_at, api_age(DATE(created_at)) AS age_in_years FROM API ORDER BY api_id")
    ]


def d_fn_days(cur, conn, p):
    a, b = _date(p, "start_date"), _date(p, "end_date")
    return [
        step(cur, "subscription_days(start_date, end_date) - Evaluated inside MySQL",
             "SELECT subscription_days(%s, %s) AS duration_days", (str(a), str(b))),
        step(cur, "subscription_days() applied across all subscriptions",
             "SELECT subscription_id, subscribe_date, expires_at, subscription_days(subscribe_date, expires_at) AS duration_days FROM SUBSCRIPTION ORDER BY subscription_id")
    ]


def d_fn_label(cur, conn, p):
    st = str(p.get("status", "ACTIVE"))[:20]
    return [
        step(cur, f"api_status_label('{st}') - Evaluated inside MySQL",
             "SELECT api_status_label(%s) AS status_description", (st,)),
        step(cur, "api_status_label() applied across all APIs",
             "SELECT api_name, status, api_status_label(status) AS status_description FROM API ORDER BY api_id")
    ]


def d_proc_owner(cur, conn, p):
    return [step(cur, "CALL get_apis_by_owner(ownerId)", "CALL get_apis_by_owner(%s)", (_int(p, "owner_id"),))]


def d_proc_api(cur, conn, p):
    return [step(cur, "CALL get_api_subscriptions(apiId)", "CALL get_api_subscriptions(%s)", (_int(p, "api_id"),))]


SPECIAL = {
    "table": d_table,
    "show_create": d_show_create,
    "unique_violation": d_unique_violation,
    "not_null_violation": d_not_null_violation,
    "fk_demo": d_fk_demo,
    "fk_cascade": d_fk_cascade,
    "ddl": d_ddl,
    "dml": d_dml,
    "dml_rollback": d_dml_rollback,
    "trigger_api": d_trigger_api,
    "trigger_sub": d_trigger_sub,
    "trigger_sweep": d_trigger_sweep,
    "fn_age": d_fn_age,
    "fn_days": d_fn_days,
    "fn_label": d_fn_label,
    "proc_owner": d_proc_owner,
    "proc_api": d_proc_api,
}


def run(key, params):
    params = params or {}
    conn = connect(dict_rows=False)
    try:
        cur = conn.cursor()
        if key in Q:
            return [step(cur, Q[key]["title"], Q[key]["sql"])]
        if key in SPECIAL:
            return SPECIAL[key](cur, conn, params)
        raise KeyError(f"Unknown demo '{key}'")
    finally:
        conn.close()


def run_query(key):
    """Used by the Reports page: returns {title, concept, explain, sql, columns, rows}."""
    d = dict(Q[key])
    conn = connect(dict_rows=False)
    try:
        r = step(conn.cursor(), d["title"], d["sql"])
    finally:
        conn.close()
    d.update(columns=r["columns"], rows=r["rows"], error=r["error"])
    return d


# --------------------------------------------------------------------------
# Page Structure: 14 Interactive Laboratory Sections
# --------------------------------------------------------------------------
def I(name, label, kind, **kw):
    return dict(name=name, label=label, kind=kind, **kw)


def section_defs():
    def item(key, title, explain, sql=None, lines=None, tables=None, inputs=None, button="Run on MySQL", define=None):
        base_q = Q.get(key, {})
        return dict(
            key=key,
            title=title,
            explain=explain,
            sql=sql if sql is not None else base_q.get("sql", ""),
            lines=lines if lines is not None else base_q.get("lines", []),
            tables=tables if tables is not None else base_q.get("tables", []),
            inputs=inputs or [],
            button=button,
            define=define,
        )

    return [
        # 1. Database Overview & Architecture
        dict(
            id="overview",
            title="1. Database Overview & Architecture",
            tables=["ROLE", "TEAM", "USER", "API", "API_VERSION", "ENDPOINT", "SUBSCRIPTION", "PERMISSION"],
            explain="The Enterprise API Governance system is built on relational DBMS principles. It consists of 8 normalized base tables, 3 views, 3 triggers, 3 stored functions, and 2 stored procedures using the InnoDB ACID storage engine and utf8mb4 collation.",
            entries=[
                item("db_objects", "Database Object Inventory", Q["db_objects"]["explain"]),
                item("db_tables_summary", "Table Storage Engine & Physical Metrics", Q["db_tables_summary"]["explain"]),
                item("show_create", "Live Schema DDL Inspection (SHOW CREATE TABLE)",
                     "Inspects the exact DDL stored in the MySQL dictionary including keys, collations, and foreign constraints.",
                     "SHOW CREATE TABLE `<table>`",
                     [{"line": "SHOW CREATE TABLE `<table>`", "text": "Reads table definition directly from MySQL dictionary."}],
                     ["all_tables"],
                     [I("table", "Table", "select", source="tables")],
                     button="Fetch Table DDL"),
            ]
        ),

        # 2. Tables and Schema Constraints
        dict(
            id="constraints",
            title="2. Tables and Schema Constraints",
            tables=["USER", "API", "API_VERSION"],
            explain="Constraints enforce domain and relational integrity at the storage engine level. MySQL guarantees that invalid data is rejected with standard errors.",
            entries=[
                item("constraints_list", "All Declared Constraints in Schema", Q["constraints_list"]["explain"]),
                item("unique_violation", "UNIQUE Constraint Enforcement Demo",
                     "Attempts to insert a duplicate email into the USER table. MySQL immediately refuses with Error 1062.",
                     "INSERT INTO `USER` (full_name, email, password_hash, role_id, team_id)\nVALUES ('Duplicate User', 'arjun@company.com', 'dummy_hash', 2, 2);",
                     [{"line": "INSERT INTO `USER` ... VALUES ('...', 'arjun@company.com', ...)", "text": "Fails because uq_user_email UNIQUE constraint prohibits duplicate emails."}],
                     ["USER"],
                     button="Test UNIQUE Rejection"),
                item("not_null_violation", "NOT NULL Constraint Enforcement Demo",
                     "Attempts to insert NULL into API.api_name. MySQL rejects the query with Error 1048.",
                     "INSERT INTO API (api_name, description, category, status, owner_id)\nVALUES (NULL, 'Missing title', 'Test', 'ACTIVE', 1);",
                     [{"line": "INSERT INTO API (api_name, ...)\nVALUES (NULL, ...)", "text": "Fails because api_name is defined as NOT NULL."}],
                     ["API"],
                     button="Test NOT NULL Rejection"),
            ]
        ),

        # 3. Primary Keys & Foreign Key Relationships
        dict(
            id="keys",
            title="3. Primary Keys & Foreign Keys",
            tables=["ROLE", "TEAM", "USER", "API", "API_VERSION", "ENDPOINT", "SUBSCRIPTION", "PERMISSION"],
            explain="PRIMARY KEYs provide unique row identification. FOREIGN KEYs maintain referential integrity. Supports RESTRICT (blocks deletion of parent rows) and CASCADE (automatically removes child records).",
            entries=[
                item("fk_list", "Foreign Key Catalog & Rules", Q["fk_list"]["explain"]),
                item("fk_demo", "Foreign Key Enforcement Demo (Errors 1451 & 1452)",
                     "Executes three illegal operations: non-existent owner, restricted deletion, and composite version mismatch. MySQL rejects all 3 with FK errors; transaction is rolled back.",
                     "1) INSERT INTO API (api_name, owner_id) VALUES ('FK test API', 9999); -- Error 1452\n"
                     "2) DELETE FROM `USER` WHERE user_id = 2; -- Error 1451 (RESTRICT)\n"
                     "3) INSERT INTO SUBSCRIPTION (api_id, version_id, consumer_id, subscribe_date) VALUES (1, 3, 4, CURDATE()); -- Error 1452 (Composite FK)",
                     [
                         {"line": "INSERT INTO API ... owner_id=9999", "text": "Rejects: owner 9999 does not exist in USER table (Error 1452)."},
                         {"line": "DELETE FROM `USER` WHERE user_id=2", "text": "Rejects: User 2 owns APIs; ON DELETE RESTRICT prevents orphan APIs (Error 1451)."},
                         {"line": "INSERT INTO SUBSCRIPTION ... (api_id=1, version_id=3)", "text": "Rejects: Version 3 belongs to API 2, not API 1; composite FK enforces matching pair (Error 1452)."}
                     ],
                     ["USER", "API", "SUBSCRIPTION", "API_VERSION"],
                     button="Execute Illegal Operations Demo"),
                item("fk_cascade", "ON DELETE CASCADE Demonstration",
                     "Proves cascade propagation: Deleting a parent API automatically cleans up child versions and grandchild endpoints in a single operation. Rolled back after verification.",
                     "DELETE FROM API WHERE api_id = <temp_api_id>;\n-- Versions and endpoints automatically cascade-deleted.",
                     [
                         {"line": "DELETE FROM API WHERE api_id = ...", "text": "Deletes the root parent API record."},
                         {"line": "API_VERSION (fk_version_api: CASCADE)", "text": "MySQL automatically deletes child API_VERSION rows."},
                         {"line": "ENDPOINT (fk_endpoint_version: CASCADE)", "text": "MySQL automatically deletes grandchild ENDPOINT rows."}
                     ],
                     ["API", "API_VERSION", "ENDPOINT"],
                     button="Run ON DELETE CASCADE Demo"),
            ]
        ),

        # 4. DDL Operations
        dict(
            id="ddl",
            title="4. DDL Operations (Data Definition Language)",
            tables=[],
            explain="Data Definition Language defines and modifies database structure (CREATE, ALTER, DROP). The demo runs the full table lifecycle on a disposable table demo_ddl_test.",
            entries=[
                item("ddl", "CREATE, ALTER and DROP Lifecycle",
                     "Executes CREATE TABLE, ALTER TABLE ADD COLUMN, ALTER TABLE DROP COLUMN, and DROP TABLE. Displays DESCRIBE after each statement.",
                     "CREATE TABLE demo_ddl_test (id INT PRIMARY KEY AUTO_INCREMENT, label VARCHAR(50) NOT NULL) ENGINE=InnoDB;\n"
                     "ALTER TABLE demo_ddl_test ADD COLUMN created_on DATE NULL;\n"
                     "ALTER TABLE demo_ddl_test DROP COLUMN created_on;\n"
                     "DROP TABLE demo_ddl_test;",
                     [
                         {"line": "CREATE TABLE demo_ddl_test (...)", "text": "Allocates schema structure with primary key."},
                         {"line": "ALTER TABLE demo_ddl_test ADD COLUMN created_on DATE NULL", "text": "Modifies table definition dynamically by adding a new attribute."},
                         {"line": "ALTER TABLE demo_ddl_test DROP COLUMN created_on", "text": "Removes the attribute from the table definition."},
                         {"line": "DROP TABLE demo_ddl_test", "text": "Destroys table structure and cleans up dictionary metadata."}
                     ],
                     button="Execute DDL Lifecycle Demo"),
            ]
        ),

        # 5. DML Operations
        dict(
            id="dml",
            title="5. DML Operations (Data Manipulation Language)",
            tables=["TEAM"],
            explain="Data Manipulation Language manipulates table rows (INSERT, SELECT, UPDATE, DELETE). ACID atomicity is demonstrated using transactions and ROLLBACK.",
            entries=[
                item("dml", "INSERT, UPDATE and DELETE on TEAM Table",
                     "Adds a temporary team, modifies its description, and deletes it, showing table state after each operation.",
                     "INSERT INTO TEAM (team_name, description) VALUES ('Demo Team (temp)', 'Temporary demonstration team');\n"
                     "UPDATE TEAM SET description = 'Updated demo description' WHERE team_name = 'Demo Team (temp)';\n"
                     "DELETE FROM TEAM WHERE team_name = 'Demo Team (temp)';",
                     [
                         {"line": "INSERT INTO TEAM ...", "text": "Inserts new row with auto-incremented primary key."},
                         {"line": "UPDATE TEAM SET description = ... WHERE ...", "text": "Modifies target row matching team_name predicate."},
                         {"line": "DELETE FROM TEAM WHERE ...", "text": "Deletes the temporary record, restoring exact initial state."}
                     ],
                     ["TEAM"],
                     button="Run DML Lifecycle Demo"),
                item("dml_rollback", "Transaction Atomicity & ROLLBACK Demo",
                     "Starts a transaction, inserts a record, observes it within the session, and executes ROLLBACK to prove the change is completely discarded.",
                     "START TRANSACTION;\n"
                     "INSERT INTO TEAM (team_name, description) VALUES ('Atomicity Team', 'Will be rolled back');\n"
                     "SELECT * FROM TEAM WHERE team_name = 'Atomicity Team'; -- Visible in session\n"
                     "ROLLBACK;\n"
                     "SELECT * FROM TEAM WHERE team_name = 'Atomicity Team'; -- Discarded completely",
                     [
                         {"line": "START TRANSACTION", "text": "Opens transaction boundary."},
                         {"line": "INSERT INTO TEAM ...", "text": "Applies modification in undo/redo transaction log."},
                         {"line": "ROLLBACK", "text": "Reverts all modifications performed in this transaction."},
                         {"line": "SELECT ...", "text": "Confirms zero persistent records remain."}
                     ],
                     ["TEAM"],
                     button="Run Transaction ROLLBACK Demo"),
            ]
        ),

        # 6. SELECT Queries & Data Filtering
        dict(
            id="select",
            title="6. SELECT Queries & Data Filtering",
            tables=["API", "SUBSCRIPTION"],
            explain="SELECT statements perform projection and selection. Demonstrates predicate filtering with WHERE, range matching with BETWEEN, string pattern matching with LIKE, and sorting with ORDER BY.",
            entries=[
                item("select_filter_apis", "Projection, Selection (WHERE) & Sorting", Q["select_filter_apis"]["explain"]),
                item("select_pattern_matching", "Wildcard Search with LIKE Operator", Q["select_pattern_matching"]["explain"]),
                item("select_range_dates", "Date Range Selection with BETWEEN & CURDATE()", Q["select_range_dates"]["explain"]),
            ]
        ),

        # 7. JOIN Operations
        dict(
            id="joins",
            title="7. JOIN Operations (INNER & LEFT)",
            tables=["API", "USER", "API_VERSION", "SUBSCRIPTION"],
            explain="A JOIN combines columns from two or more tables using relational keys. INNER JOIN returns matching rows only; LEFT JOIN preserves all rows from the left table even if no match exists.",
            entries=[
                item("inner_api_owner", Q["inner_api_owner"]["title"], Q["inner_api_owner"]["explain"]),
                item("inner_subscription", Q["inner_subscription"]["title"], Q["inner_subscription"]["explain"]),
                item("left_versions", Q["left_versions"]["title"], Q["left_versions"]["explain"]),
                item("left_users_subs", Q["left_users_subs"]["title"], Q["left_users_subs"]["explain"]),
            ]
        ),

        # 8. Aggregate Functions
        dict(
            id="aggregates",
            title="8. Aggregate Functions",
            tables=["SUBSCRIPTION", "API"],
            explain="Aggregate functions (COUNT, SUM, AVG, MAX, MIN) reduce multiple row values into a single summary result.",
            entries=[
                item("agg_all", Q["agg_all"]["title"], Q["agg_all"]["explain"]),
                item("agg_api", Q["agg_api"]["title"], Q["agg_api"]["explain"]),
            ]
        ),

        # 9. GROUP BY and HAVING
        dict(
            id="group_having",
            title="9. GROUP BY and HAVING Clauses",
            tables=["API", "SUBSCRIPTION", "TEAM", "USER"],
            explain="GROUP BY collapses rows with identical values into summary groups. WHERE filters individual rows BEFORE grouping; HAVING filters aggregated groups AFTER group creation.",
            entries=[
                item("group_by", Q["group_by"]["title"], Q["group_by"]["explain"]),
                item("having", Q["having"]["title"], Q["having"]["explain"]),
                item("team_having", Q["team_having"]["title"], Q["team_having"]["explain"]),
            ]
        ),

        # 10. Subqueries & Nested Queries
        dict(
            id="subqueries",
            title="10. Subqueries & Nested Queries",
            tables=["API", "SUBSCRIPTION", "API_VERSION"],
            explain="A subquery is a SELECT statement nested inside an outer SQL query. Includes scalar subqueries (returning 1 value), IN subqueries (list membership), correlated subqueries (referencing outer rows), and derived tables in HAVING.",
            entries=[
                item("sub_in", Q["sub_in"]["title"], Q["sub_in"]["explain"]),
                item("sub_not_exists", Q["sub_not_exists"]["title"], Q["sub_not_exists"]["explain"]),
                item("sub_scalar", Q["sub_scalar"]["title"], Q["sub_scalar"]["explain"]),
                item("sub_derived", Q["sub_derived"]["title"], Q["sub_derived"]["explain"]),
            ]
        ),

        # 11. Database Views
        dict(
            id="views",
            title="11. Database Views (Virtual Tables)",
            tables=["api_details_view", "api_version_view", "subscription_details_view"],
            explain="A VIEW is a stored query that presents data as a virtual table. The join and projection logic is executed inside MySQL, simplifying client queries and securing base table structures.",
            entries=[
                item("view_api_details", "api_details_view (API JOIN USER)", Q["view_api_details"]["explain"], define=("VIEW", "api_details_view")),
                item("view_api_version", "api_version_view (API JOIN API_VERSION)", Q["view_api_version"]["explain"], define=("VIEW", "api_version_view")),
                item("view_subscription", "subscription_details_view (4-Table JOIN View)", Q["view_subscription"]["explain"], define=("VIEW", "subscription_details_view")),
                item("view_filtered", "Querying & Filtering a Database View", Q["view_filtered"]["explain"]),
            ]
        ),

        # 12. Stored Functions
        dict(
            id="functions",
            title="12. Stored Functions",
            tables=["API", "SUBSCRIPTION"],
            explain="A stored function is compiled in MySQL, accepts parameters, and returns a scalar value. Can be invoked directly within any SELECT, WHERE, or ORDER BY clause.",
            entries=[
                item("fn_age", "api_age(api_date) - Age in Whole Years",
                     "Calculates years between date and CURDATE() via TIMESTAMPDIFF(YEAR, api_date, CURDATE()). Non-deterministic.",
                     "SELECT api_age('<date>');",
                     [
                         {"line": "CREATE FUNCTION api_age(api_date DATE) RETURNS INT", "text": "Accepts input date, returns integer years."},
                         {"line": "NOT DETERMINISTIC NO SQL", "text": "Not deterministic because output depends on current system date."},
                         {"line": "RETURN TIMESTAMPDIFF(YEAR, api_date, CURDATE());", "text": "Computes exact elapsed calendar years."}
                     ],
                     ["API"],
                     [I("api_date", "Candidate Date", "date", default="2022-01-15")],
                     button="Execute api_age()",
                     define=("FUNCTION", "api_age")),
                item("fn_days", "subscription_days(start_date, end_date) - Duration in Days",
                     "Computes day difference via DATEDIFF(end_date, start_date). Deterministic.",
                     "SELECT subscription_days('<start>', '<end>');",
                     [
                         {"line": "CREATE FUNCTION subscription_days(start_date DATE, end_date DATE) RETURNS INT", "text": "Accepts start and end dates."},
                         {"line": "DETERMINISTIC NO SQL", "text": "Deterministic: identical date inputs always return the identical day count."},
                         {"line": "RETURN DATEDIFF(end_date, start_date);", "text": "Subtracts start from end to obtain day difference."}
                     ],
                     ["SUBSCRIPTION"],
                     [I("start_date", "Start Date", "date", default="2026-03-01"), I("end_date", "End Date", "date", default="2027-03-01")],
                     button="Execute subscription_days()",
                     define=("FUNCTION", "subscription_days")),
                item("fn_label", "api_status_label(status) - Status Descriptor",
                     "Evaluates input status string using a CASE expression stored in the database.",
                     "SELECT api_status_label('<status>');",
                     [
                         {"line": "CREATE FUNCTION api_status_label(api_status VARCHAR(20)) RETURNS VARCHAR(50)", "text": "Returns descriptive English text for API status codes."},
                         {"line": "RETURN CASE UPPER(...) WHEN 'ACTIVE' THEN 'API is active' ...", "text": "Evaluates status with branch cases."}
                     ],
                     ["API"],
                     [I("status", "Status Code", "select", source="statuses")],
                     button="Execute api_status_label()",
                     define=("FUNCTION", "api_status_label")),
            ]
        ),

        # 13. Stored Procedures
        dict(
            id="procedures",
            title="13. Stored Procedures",
            tables=["API", "SUBSCRIPTION"],
            explain="A stored procedure is a reusable, precompiled block of SQL invoked via CALL. It can accept IN/OUT parameters and return full tabular result sets to the application.",
            entries=[
                item("proc_owner", "CALL get_apis_by_owner(ownerId)",
                     "Invokes stored procedure returning all APIs owned by the selected user ID.",
                     "CALL get_apis_by_owner(<ownerId>);",
                     [
                         {"line": "CREATE PROCEDURE get_apis_by_owner(IN ownerId INT)", "text": "Precompiled procedure taking input owner ID."},
                         {"line": "SELECT api_id, api_name, category, status ... WHERE owner_id = ownerId", "text": "Executes optimized query and streams result set back to caller."}
                     ],
                     ["API"],
                     [I("owner_id", "Owner", "select", source="owners")],
                     button="CALL get_apis_by_owner()",
                     define=("PROCEDURE", "get_apis_by_owner")),
                item("proc_api", "CALL get_api_subscriptions(apiId)",
                     "Invokes stored procedure returning all consumers and subscriptions for the selected API.",
                     "CALL get_api_subscriptions(<apiId>);",
                     [
                         {"line": "CREATE PROCEDURE get_api_subscriptions(IN apiId INT)", "text": "Precompiled procedure taking input API ID."},
                         {"line": "JOIN API, `USER`, API_VERSION ... WHERE S.api_id = apiId", "text": "Resolves all subscriptions and orders newest first."}
                     ],
                     ["SUBSCRIPTION", "USER", "API", "API_VERSION"],
                     [I("api_id", "API", "select", source="apis")],
                     button="CALL get_api_subscriptions()",
                     define=("PROCEDURE", "get_api_subscriptions")),
            ]
        ),

        # 14. Database Triggers
        dict(
            id="triggers",
            title="14. Database Triggers (Active Rules)",
            tables=["API", "API_VERSION", "SUBSCRIPTION"],
            explain="Triggers are event-driven programs stored in MySQL that fire automatically upon INSERT, UPDATE, or DELETE on a table. The application does not implement business enforcement—the database engine itself guarantees consistency.",
            entries=[
                item("trigger_list", "Registered Triggers in MySQL Dictionary", Q["trigger_list"]["explain"]),
                item("trigger_api", "after_api_deprecated (AFTER UPDATE ON API)",
                     "When an API status changes to DEPRECATED, MySQL automatically sets all its ACTIVE versions to DEPRECATED with CURDATE().",
                     "UPDATE API SET status = 'DEPRECATED' WHERE api_id = <id>;\n-- Versions automatically update via trigger after_api_deprecated.",
                     [
                         {"line": "CREATE TRIGGER after_api_deprecated AFTER UPDATE ON API", "text": "Listens for UPDATE events on the API table."},
                         {"line": "FOR EACH ROW BEGIN IF NEW.status = 'DEPRECATED' AND OLD.status <> 'DEPRECATED'", "text": "Checks if status transitioned to DEPRECATED."},
                         {"line": "UPDATE API_VERSION SET status = 'DEPRECATED', deprecated_date = COALESCE(..., CURDATE())", "text": "Automatically mutates dependent versions inside the engine."}
                     ],
                     ["API", "API_VERSION"],
                     button="Run API Deprecation Trigger Demo",
                     define=("TRIGGER", "after_api_deprecated")),
                item("trigger_sub", "check_subscription_expiry (+ _insert) (BEFORE INSERT/UPDATE)",
                     "BEFORE INSERT / BEFORE UPDATE on SUBSCRIPTION: If an active subscription has an expired date, the trigger intercepts and overrides the status to EXPIRED.",
                     "INSERT INTO SUBSCRIPTION ... (expires_at in past) -> Status automatically becomes EXPIRED.\n"
                     "UPDATE SUBSCRIPTION ... (expires_at in past) -> Status forced to EXPIRED.",
                     [
                         {"line": "CREATE TRIGGER check_subscription_expiry BEFORE UPDATE ON SUBSCRIPTION", "text": "Fires before row is written to disk."},
                         {"line": "IF NEW.expires_at IS NOT NULL AND NEW.expires_at < CURDATE()", "text": "Checks if expiry date is prior to current date."},
                         {"line": "SET NEW.status = 'EXPIRED';", "text": "Forces the column value to EXPIRED before committing row."}
                     ],
                     ["SUBSCRIPTION"],
                     button="Run Subscription Expiry Trigger Demo",
                     define=("TRIGGER", "check_subscription_expiry")),
                item("trigger_sweep", "Expiry Sweep Simulation with Time-Travel",
                     "Simulates a future date using SET SESSION TIMESTAMP and performs a no-op sweep. MySQL's trigger marks overdue subscriptions as EXPIRED.",
                     "SET SESSION TIMESTAMP = UNIX_TIMESTAMP('<date> 12:00:00');\n"
                     "UPDATE SUBSCRIPTION SET expires_at = expires_at WHERE status = 'ACTIVE' AND expires_at < CURDATE();",
                     [
                         {"line": "SET SESSION TIMESTAMP = UNIX_TIMESTAMP('<date>');", "text": "Temporarily fast-forwards session time for the connection."},
                         {"line": "UPDATE SUBSCRIPTION SET expires_at = expires_at ...", "text": "No-op UPDATE that triggers BEFORE UPDATE on all overdue rows."}
                     ],
                     ["SUBSCRIPTION"],
                     [I("sim_date", "Simulated Today Date", "date", default="2027-03-10")],
                     button="Run Time-Travel Sweep Demo"),
            ]
        ),
    ]


def definition(kind, name):
    allowed = {
        "VIEW": VIEWS,
        "TRIGGER": ["after_api_deprecated", "check_subscription_expiry", "check_subscription_expiry_insert"],
        "FUNCTION": ["api_age", "subscription_days", "api_status_label"],
        "PROCEDURE": ["get_apis_by_owner", "get_api_subscriptions"],
    }
    if name not in allowed.get(kind, []):
        return None
    conn = connect(dict_rows=True)
    try:
        cur = conn.cursor()
        cur.execute(f"SHOW CREATE {kind} `{name}`")
        row = cur.fetchone()
        for k, v in row.items():
            if k.startswith("Create") or k == "SQL Original Statement":
                return clean(v)
    finally:
        conn.close()
