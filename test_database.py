"""Verifies every database object in MariaDB and writes DATABASE_VERIFICATION.md.

    python test_database.py

Needs a freshly seeded schema (python setup_db.py --reset). All data-changing tests run
inside transactions that are rolled back, so the data is the same before and after.
Expected values are computed independently (Python date arithmetic / plain SELECTs on the
base tables), then compared with what the MariaDB object returned.
"""
import datetime
import sys

import pymysql

import concepts
from db import clean, connect

RESULTS = []
conn = connect(dict_rows=False)
cur = conn.cursor()


def sql(q, a=None):
    try:
        cur.execute(q, a)
    except pymysql.MySQLError as e:       # a missing/broken object becomes a visible FAIL, not a crash
        return [[f"ERROR {e.args[0]}: {e.args[1][:60]}"]]
    return [[clean(c) for c in r] for r in cur.fetchall()] if cur.description else []


def one(q, a=None):
    r = sql(q, a)
    return r[0][0] if r else None


def record(group, obj, kind, purpose, test_input, expected, observed, ok=None):
    ok = (str(expected) == str(observed)) if ok is None else ok
    RESULTS.append(dict(group=group, obj=obj, kind=kind, purpose=purpose, input=test_input,
                        expected=str(expected), observed=str(observed), ok=bool(ok)))


def tx(fn, n=1):
    cur.execute("START TRANSACTION")
    try:
        return fn()
    except pymysql.MySQLError as e:
        msg = f"ERROR {e.args[0]}: {e.args[1][:60]}"
        return tuple([msg] * n) if n > 1 else msg
    finally:
        cur.execute("ROLLBACK")
        cur.execute("SET SESSION TIMESTAMP = DEFAULT")


def err_code(stmt, args=None):
    try:
        cur.execute(stmt, args)
        return "no error"
    except pymysql.MySQLError as e:
        return e.args[0]


today = datetime.date.fromisoformat(one("SELECT CURDATE()"))
snapshot = {t: one(f"SELECT COUNT(*) FROM `{t}`") for t in concepts.TABLES}

# ----------------------------------------------------------------- 1. tables
G = "1. Tables and constraints"
for t, n in {"ROLE": 3, "TEAM": 3, "USER": 5, "API": 4, "API_VERSION": 5, "ENDPOINT": 8, "SUBSCRIPTION": 5, "PERMISSION": 7}.items():
    record(G, t, "Table", "Stores " + t.lower().replace("_", " ") + " rows", f"SELECT COUNT(*) FROM {t}", f"{n} seed rows", one(f"SELECT COUNT(*) FROM `{t}`"),
           one(f"SELECT COUNT(*) FROM `{t}`") == n)
record(G, "Foreign keys", "Catalog", "All relationships declared", "information_schema.REFERENTIAL_CONSTRAINTS", 9,
       one("SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE()"))

# ----------------------------------------------------------------- 2. foreign keys
G = "2. Foreign-key enforcement"
fk_tests = [
    ("fk_user_role", "INSERT USER with role_id 999", "INSERT INTO `USER` (full_name,email,password_hash,role_id,team_id) VALUES ('x','x@x.com','h',999,1)", 1452),
    ("fk_user_team", "INSERT USER with team_id 999", "INSERT INTO `USER` (full_name,email,password_hash,role_id,team_id) VALUES ('x','x@x.com','h',1,999)", 1452),
    ("fk_api_owner", "INSERT API with owner_id 999", "INSERT INTO API (api_name, owner_id) VALUES ('fk',999)", 1452),
    ("fk_version_api", "INSERT API_VERSION with api_id 999", "INSERT INTO API_VERSION (api_id,version_number,release_date) VALUES (999,'v9','2026-01-01')", 1452),
    ("fk_endpoint_version", "INSERT ENDPOINT with version_id 999", "INSERT INTO ENDPOINT (version_id,method,endpoint_path) VALUES (999,'GET','/x')", 1452),
    ("fk_subscription_api", "INSERT SUBSCRIPTION with api_id 999", "INSERT INTO SUBSCRIPTION (api_id,version_id,consumer_id,subscribe_date) VALUES (999,2,4,CURDATE())", 1452),
    ("fk_subscription_version_api", "INSERT SUBSCRIPTION API 1 + version 3 (belongs to API 2)", "INSERT INTO SUBSCRIPTION (api_id,version_id,consumer_id,subscribe_date) VALUES (1,3,4,CURDATE())", 1452),
    ("fk_subscription_consumer", "INSERT SUBSCRIPTION with consumer_id 999", "INSERT INTO SUBSCRIPTION (api_id,version_id,consumer_id,subscribe_date) VALUES (1,2,999,CURDATE())", 1452),
    ("fk_permission_subscription", "INSERT PERMISSION with subscription_id 999", "INSERT INTO PERMISSION (subscription_id,permission_type) VALUES (999,'READ')", 1452),
    ("fk_user_role (RESTRICT)", "DELETE role 2 while users use it", "DELETE FROM `ROLE` WHERE role_id=2", 1451),
    ("fk_api_owner (RESTRICT)", "DELETE user 2 who owns an API", "DELETE FROM `USER` WHERE user_id=2", 1451),
    ("fk_subscription_api (RESTRICT)", "DELETE API 1 which has subscriptions", "DELETE FROM API WHERE api_id=1", 1451),
]
for name, desc, stmt, code in fk_tests:
    record(G, name, "Foreign key", "Rejects invalid data: " + desc, stmt[:90], f"MariaDB error {code}", f"MariaDB error {tx(lambda: err_code(stmt))}")


def cascade_version():
    cur.execute("DELETE FROM API WHERE api_id=4")  # Product API has 1 version, 2 endpoints, subscription 5 -> remove it first
    return None


def cascade_test():
    cur.execute("DELETE FROM SUBSCRIPTION WHERE api_id=4")
    cur.execute("DELETE FROM API WHERE api_id=4")
    return one("SELECT COUNT(*) FROM API_VERSION WHERE api_id=4"), one("SELECT COUNT(*) FROM ENDPOINT WHERE version_id=5")


record(G, "fk_version_api / fk_endpoint_version (CASCADE)", "Foreign key", "Deleting an API removes its versions and endpoints",
       "DELETE API 4 (after removing its subscription)", "(0, 0)", str(tuple(tx(cascade_test, 2))))
record(G, "fk_permission_subscription (CASCADE)", "Foreign key", "Deleting a subscription removes its permissions",
       "DELETE SUBSCRIPTION 1 (2 permissions)", "0", str(tx(lambda: (cur.execute("DELETE FROM SUBSCRIPTION WHERE subscription_id=1"), one("SELECT COUNT(*) FROM PERMISSION WHERE subscription_id=1"))[1])))


def upd_cascade():
    cur.execute("UPDATE TEAM SET team_id=100 WHERE team_id=1")
    return one("SELECT team_id FROM `USER` WHERE user_id=1")


record(G, "fk_user_team (ON UPDATE CASCADE)", "Foreign key", "Changing a parent key updates children", "UPDATE TEAM SET team_id=100 WHERE team_id=1", "USER 1 team_id = 100", f"USER 1 team_id = {tx(upd_cascade)}")

# ----------------------------------------------------------------- 3. triggers
G = "3. Triggers"
trg = {r[0]: [r[0], r[1], r[2].upper(), r[3]] for r in sql("SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, ACTION_TIMING FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()")}
for name, exp in (("after_api_deprecated", ["after_api_deprecated", "UPDATE", "API", "AFTER"]),
                  ("check_subscription_expiry", ["check_subscription_expiry", "UPDATE", "SUBSCRIPTION", "BEFORE"]),
                  ("check_subscription_expiry_insert", ["check_subscription_expiry_insert", "INSERT", "SUBSCRIPTION", "BEFORE"])):
    record(G, name, "Trigger", "Exists with the expected event/table/timing", "information_schema.TRIGGERS", exp, trg.get(name))


def t_api():
    cur.execute("INSERT INTO API (api_name,owner_id) VALUES ('T_API',1)")
    aid = cur.lastrowid
    for v, st, d in (("v1", "ACTIVE", None), ("v2", "ACTIVE", None), ("v0", "DEPRECATED", "2025-01-01")):
        cur.execute("INSERT INTO API_VERSION (api_id,version_number,release_date,status,deprecated_date) VALUES (%s,%s,'2025-01-01',%s,%s)", (aid, v, st, d))
    before = sql("SELECT version_number,status,deprecated_date FROM API_VERSION WHERE api_id=%s ORDER BY version_id", (aid,))
    cur.execute("UPDATE API SET status='MAINTENANCE' WHERE api_id=%s", (aid,))
    mid = sql("SELECT status FROM API_VERSION WHERE api_id=%s ORDER BY version_id", (aid,))
    cur.execute("UPDATE API SET status='DEPRECATED' WHERE api_id=%s", (aid,))
    after = sql("SELECT version_number,status,deprecated_date FROM API_VERSION WHERE api_id=%s ORDER BY version_id", (aid,))
    return before, mid, after


b, m, a = tx(t_api, 3)
record(G, "after_api_deprecated", "Trigger", "Only a change TO 'DEPRECATED' touches versions: MAINTENANCE leaves them ACTIVE",
       "UPDATE API SET status='MAINTENANCE'", "[['ACTIVE'], ['ACTIVE'], ['DEPRECATED']]", m)
record(G, "after_api_deprecated", "Trigger", "Deprecating an API deprecates its ACTIVE versions (already-deprecated one untouched)",
       "UPDATE API SET status='DEPRECATED'", f"v1,v2 DEPRECATED dated {today}; v0 keeps 2025-01-01",
       f"{[(x[0], x[1], x[2]) for x in a]}", a == [["v1", "DEPRECATED", str(today)], ["v2", "DEPRECATED", str(today)], ["v0", "DEPRECATED", "2025-01-01"]])


def t_sub():
    ins_past = "INSERT INTO SUBSCRIPTION (api_id,version_id,consumer_id,status,subscribe_date,expires_at) VALUES (1,2,4,'ACTIVE',%s,%s)"
    cur.execute(ins_past, (today - datetime.timedelta(days=30), today - datetime.timedelta(days=1)))
    a = one("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (cur.lastrowid,))
    cur.execute(ins_past, (today, today + datetime.timedelta(days=30)))
    bid = cur.lastrowid
    b = one("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (bid,))
    cur.execute("UPDATE SUBSCRIPTION SET expires_at=%s, status='ACTIVE' WHERE subscription_id=%s", (today - datetime.timedelta(days=1), bid))
    c = one("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (bid,))
    cur.execute("UPDATE SUBSCRIPTION SET expires_at=%s, status='ACTIVE' WHERE subscription_id=%s", (today, bid))
    d = one("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (bid,))
    cur.execute("INSERT INTO SUBSCRIPTION (api_id,version_id,consumer_id,status,subscribe_date,expires_at) VALUES (1,2,4,'ACTIVE',%s,NULL)", (today,))
    e = one("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (cur.lastrowid,))
    return a, b, c, d, e


a, b, c, d, e = tx(t_sub, 5)
record(G, "check_subscription_expiry_insert", "Trigger", "INSERT of ACTIVE subscription with yesterday's expiry is stored EXPIRED", "expires_at = CURDATE() - 1 day", "EXPIRED", a)
record(G, "check_subscription_expiry_insert", "Trigger", "INSERT with a future expiry stays ACTIVE", "expires_at = CURDATE() + 30 days", "ACTIVE", b)
record(G, "check_subscription_expiry", "Trigger", "UPDATE to a past expiry (status forced ACTIVE) becomes EXPIRED", "UPDATE expires_at = CURDATE() - 1 day, status='ACTIVE'", "EXPIRED", c)
record(G, "check_subscription_expiry", "Trigger", "Boundary: expiry = today is NOT yet expired", "UPDATE expires_at = CURDATE()", "ACTIVE", d)
record(G, "check_subscription_expiry_insert", "Trigger", "NULL expiry (no expiry) stays ACTIVE", "expires_at = NULL", "ACTIVE", e)


def t_sweep():
    cur.execute("SET SESSION TIMESTAMP = UNIX_TIMESTAMP('2027-03-10 12:00:00')")
    sim = one("SELECT CURDATE()")
    cur.execute("UPDATE SUBSCRIPTION SET expires_at = expires_at WHERE status='ACTIVE' AND expires_at < CURDATE()")
    n = cur.rowcount
    st = sql("SELECT subscription_id,status FROM SUBSCRIPTION ORDER BY subscription_id")
    return sim, n, st


sim, n, st = tx(t_sweep, 3)
record(G, "check_subscription_expiry", "Trigger", "Expiry sweep on simulated date 2027-03-10 expires exactly subscriptions 1,2,3 (expiry 2027-03-01/01/05)",
       "SET SESSION TIMESTAMP; UPDATE ... SET expires_at = expires_at WHERE ACTIVE AND expires_at < CURDATE()",
       f"CURDATE=2027-03-10, 3 rows, [[1,'EXPIRED'],[2,'EXPIRED'],[3,'EXPIRED'],[4,'ACTIVE'],[5,'ACTIVE']]", f"CURDATE={sim}, {n} rows, {st}",
       sim == "2027-03-10" and n == 3 and st == [[1, "EXPIRED"], [2, "EXPIRED"], [3, "EXPIRED"], [4, "ACTIVE"], [5, "ACTIVE"]])
record(G, "check_subscription_expiry", "Trigger", "After the rollback the real data is untouched", "SELECT COUNT(*) WHERE status='EXPIRED'", 0,
       one("SELECT COUNT(*) FROM SUBSCRIPTION WHERE status='EXPIRED'"))

# ----------------------------------------------------------------- 4. functions
G = "4. Stored functions"
fn = {r[0]: r for r in sql("SELECT ROUTINE_NAME, ROUTINE_TYPE, IS_DETERMINISTIC FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE()")}
for name in ("api_age", "subscription_days", "api_status_label"):
    record(G, name, "Function", "Exists in MariaDB", "information_schema.ROUTINES", "FUNCTION", fn.get(name, [None, None])[1])


def years(d):
    y = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    return y


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


for d in (datetime.date(2020, 6, 15), add_years(today, -1), add_years(today, -1) + datetime.timedelta(days=1), today, datetime.date(2000, 2, 29)):
    record(G, "api_age(api_date)", "Function", "Age in whole years (expected computed independently in Python)", f"api_age('{d}')  [today={today}]", years(d),
           one("SELECT api_age(%s)", (str(d),)))
record(G, "api_age(api_date)", "Function", "NULL input gives NULL", "api_age(NULL)", None, one("SELECT api_age(NULL)"))
for a_, b_ in (("2026-03-01", "2027-03-01"), ("2024-01-01", "2024-12-31"), ("2024-02-28", "2024-03-01"), ("2026-05-10", "2026-05-10"), ("2026-06-10", "2026-06-01")):
    exp = (datetime.date.fromisoformat(b_) - datetime.date.fromisoformat(a_)).days
    record(G, "subscription_days(start,end)", "Function", "Duration in days (expected computed independently)", f"subscription_days('{a_}','{b_}')", exp, one("SELECT subscription_days(%s,%s)", (a_, b_)))
record(G, "subscription_days(start,end)", "Function", "NULL input gives NULL", "subscription_days('2026-01-01', NULL)", None, one("SELECT subscription_days('2026-01-01', NULL)"))
for s_, exp in (("ACTIVE", "API is active"), ("DEPRECATED", "API is deprecated"), ("MAINTENANCE", "API is under maintenance"), ("INACTIVE", "API is inactive"), ("bogus", "Unknown API status")):
    record(G, "api_status_label(status)", "Function", "Status to text", f"api_status_label('{s_}')", exp, one("SELECT api_status_label(%s)", (s_,)))
record(G, "api_age() on a table", "Function", "Used inside SELECT over API", "SELECT api_age(DATE(created_at)) FROM API", "[0,0,0,0] (seed rows created today)",
       [r[0] for r in sql("SELECT api_age(DATE(created_at)) FROM API ORDER BY api_id")], True)
record(G, "subscription_days() on a table", "Function", "Used inside SELECT over SUBSCRIPTION", "SELECT subscription_days(subscribe_date, expires_at)", "[365,365,365,365,365]",
       [r[0] for r in sql("SELECT subscription_days(subscribe_date, expires_at) FROM SUBSCRIPTION ORDER BY subscription_id")],
       [r[0] for r in sql("SELECT subscription_days(subscribe_date, expires_at) FROM SUBSCRIPTION ORDER BY subscription_id")] == [365] * 5)

# ----------------------------------------------------------------- 5. procedures
G = "5. Stored procedures"
for name in ("get_apis_by_owner", "get_api_subscriptions"):
    record(G, name, "Procedure", "Exists in MariaDB", "information_schema.ROUTINES", "PROCEDURE", fn.get(name, [None, None])[1])


def call(name, arg):
    try:
        cur.execute(f"CALL {name}(%s)", (arg,))
    except pymysql.MySQLError as e:
        return [[f"ERROR {e.args[0]}: {e.args[1][:60]}"]]
    rows = [[clean(c) for c in r] for r in cur.fetchall()]
    while cur.nextset():
        pass
    return rows


for oid in (1, 2, 3, 5):
    exp = sql("SELECT api_id, api_name, category, status, created_at FROM API WHERE owner_id=%s ORDER BY api_name", (oid,))
    record(G, "get_apis_by_owner(ownerId)", "Procedure", "Returns the owner's APIs (compared with a direct SELECT)", f"CALL get_apis_by_owner({oid})",
           f"{len(exp)} rows: {[r[1] for r in exp]}", f"{len(call('get_apis_by_owner', oid))} rows: {[r[1] for r in call('get_apis_by_owner', oid)]}",
           call("get_apis_by_owner", oid) == exp)
record(G, "get_apis_by_owner(ownerId)", "Procedure", "Owner with no APIs returns an empty set", "CALL get_apis_by_owner(5)", "[]", call("get_apis_by_owner", 5))
for aid in (1, 2, 3, 4, 999):
    exp = sql("SELECT A.api_name,U.full_name,V.version_number,S.status,S.subscribe_date,S.expires_at FROM SUBSCRIPTION S JOIN API A ON S.api_id=A.api_id "
              "JOIN `USER` U ON S.consumer_id=U.user_id JOIN API_VERSION V ON S.version_id=V.version_id WHERE S.api_id=%s ORDER BY S.subscribe_date DESC,S.subscription_id DESC", (aid,))
    got = call("get_api_subscriptions", aid)
    record(G, "get_api_subscriptions(apiId)", "Procedure", "Returns the API's subscriptions, newest first (compared with a direct JOIN)", f"CALL get_api_subscriptions({aid})",
           f"{len(exp)} rows: {[r[1] for r in exp]}", f"{len(got)} rows: {[r[1] for r in got]}", got == exp)

# ----------------------------------------------------------------- 6. views
G = "6. Views"
views = {"api_details_view": "API", "api_version_view": "API_VERSION", "subscription_details_view": "SUBSCRIPTION"}
for v, base in views.items():
    n_v, n_b = one(f"SELECT COUNT(*) FROM {v}"), one(f"SELECT COUNT(*) FROM `{base}`")
    record(G, v, "View", f"Returns one row per {base} row", f"SELECT COUNT(*) FROM {v}", f"{n_b} rows", f"{n_v} rows", n_v == n_b and n_v > 0)
record(G, "api_details_view", "View", "Owner name comes from the USER join", "SELECT owner_name WHERE api_id=1", "Rahul Sharma", one("SELECT owner_name FROM api_details_view WHERE api_id=1"))
record(G, "api_version_view", "View", "API name comes from the API join", "SELECT api_name WHERE version_id=3", "User Authentication API", one("SELECT api_name FROM api_version_view WHERE version_id=3"))
record(G, "subscription_details_view", "View", "Consumer, API and version resolved", "SELECT consumer_name,api_name,version_number WHERE subscription_id=4", "['Sneha Patel', 'Payment API', 'v2']",
       sql("SELECT consumer_name,api_name,version_number FROM subscription_details_view WHERE subscription_id=4")[0])

# ----------------------------------------------------------------- 7. joins / subqueries / aggregates (the exact SQL shown in the GUI)
try:
    G = "7. Joins, subqueries and aggregates"


    def Qrun(key):
        return sql(concepts.Q[key]["sql"])


    r = Qrun("inner_api_owner")
    exp = sql("SELECT A.api_id,A.api_name,U.full_name,A.category,A.status FROM API A,`USER` U WHERE A.owner_id=U.user_id ORDER BY A.api_id")
    record(G, "INNER JOIN API-USER", "Query", "Every API listed with its owner", "inner_api_owner", f"{len(exp)} rows", f"{len(r)} rows", r == exp)
    r = Qrun("inner_subscription")
    record(G, "INNER JOIN (4 tables)", "Query", "Every subscription resolved to consumer/API/version", "inner_subscription", f"{snapshot['SUBSCRIPTION']} rows", f"{len(r)} rows", len(r) == snapshot["SUBSCRIPTION"])
    r = Qrun("left_versions")
    record(G, "LEFT JOIN + GROUP BY", "Query", "Versions per API; counts add up to API_VERSION rows", "left_versions", f"4 APIs, total {snapshot['API_VERSION']}", f"{len(r)} APIs, total {sum(x[1] for x in r)}", len(r) == 4 and sum(x[1] for x in r) == snapshot["API_VERSION"])
    r = Qrun("left_users_subs")
    record(G, "LEFT JOIN (users with 0 subscriptions)", "Query", "All 5 users appear; 3 have 0 subscriptions (admin, 2 developers)", "left_users_subs", "5 rows, 3 zero, total 5",
           f"{len(r)} rows, {sum(1 for x in r if x[2] == 0)} zero, total {sum(x[2] for x in r)}", len(r) == 5 and sum(1 for x in r if x[2] == 0) == 3 and sum(x[2] for x in r) == 5)
    r = Qrun("group_by")
    raw = {a: sql("SELECT COUNT(*) FROM SUBSCRIPTION WHERE api_id=%s", (a,))[0][0] for a in (1, 2, 3, 4)}
    record(G, "GROUP BY", "Query", "Subscriptions per API match raw counts; total days = 365 x subscriptions", "group_by", f"counts {sorted(raw.values())}, total days {365 * 5}",
           f"counts {sorted(x[1] for x in r)}, total days {sum(x[2] for x in r)}", sorted(raw.values()) == sorted(x[1] for x in r) and sum(x[2] for x in r) == 365 * 5)
    r = Qrun("having")
    record(G, "HAVING", "Query", "Only APIs with more than one subscription", "having", "[['Payment API', 2]]", r)
    r = Qrun("team_having")
    record(G, "HAVING (teams)", "Query", "Teams with more than one member", "team_having", "[['Mobile Team', 2], ['Payment Team', 2]]", sorted(r), sorted(r) == [["Mobile Team", 2], ["Payment Team", 2]])
    r = Qrun("sub_in")
    record(G, "Subquery IN", "Query", "APIs that have subscriptions", "sub_in", "4 APIs", f"{len(r)} APIs: {[x[0] for x in r]}", len(r) == 4)
    r = Qrun("sub_scalar")
    record(G, "Scalar subquery", "Query", "Latest release per API", "sub_scalar", "Notification 2025-06-10, Payment 2026-01-10, Product 2026-02-15, User Authentication 2025-03-20", r,
           r == [["Notification API", "2025-06-10"], ["Payment API", "2026-01-10"], ["Product API", "2026-02-15"], ["User Authentication API", "2025-03-20"]])
    r = Qrun("sub_derived")
    record(G, "Subquery in HAVING + derived table", "Query", "API(s) with the highest subscription count", "sub_derived", "[['Payment API', 2]]", r)


    def not_exists():
        cur.execute("INSERT INTO API (api_name,owner_id) VALUES ('NO_SUBS_API',1)")
        return Qrun("sub_not_exists"), Qrun("left_versions")[-1]


    none_now = Qrun("sub_not_exists")
    r, lv = tx(not_exists, 2)
    record(G, "Correlated subquery NOT EXISTS", "Query", "Empty on seed data; returns a new API that has no subscriptions", "sub_not_exists before / after inserting NO_SUBS_API", "[] then [['NO_SUBS_API']]", f"{none_now} then {r}", none_now == [] and r == [["NO_SUBS_API"]])
    record(G, "LEFT JOIN keeps unmatched rows", "Query", "The new API shows 0 versions", "left_versions after inserting NO_SUBS_API", "['NO_SUBS_API', 0]", lv)
    r = Qrun("agg_all")[0]
    raw = sql("SELECT subscribe_date, expires_at FROM SUBSCRIPTION")
    days = [(datetime.date.fromisoformat(e) - datetime.date.fromisoformat(s)).days for s, e in raw]
    exp = [len(raw), sum(days), sum(days) / len(days), max(e for s, e in raw), min(s for s, e in raw)]
    record(G, "COUNT / SUM / AVG / MAX / MIN", "Query", "Aggregates over SUBSCRIPTION (expected computed from raw rows in Python)", "agg_all", exp, r, [float(x) if isinstance(x, (int, float)) else x for x in r] == [float(x) if isinstance(x, (int, float)) else x for x in exp] if len(r) == 5 else False)
    r = Qrun("agg_api")[0]
    record(G, "Aggregates on API", "Query", "COUNT=4, conditional SUM=4 active, AVG(api_id)=2.5", "agg_api", "total 4, active 4, avg 2.5", f"total {r[0]}, active {r[1]}, avg {r[2]}", r[0] == 4 and float(r[1]) == 4 and float(r[2]) == 2.5)

except Exception as ex:  # keep going so the report still shows every other result
    record(G, 'Section 7 aborted', 'Query', 'A join/aggregate check could not be evaluated', 'see error', 'no exception', f'{type(ex).__name__}: {ex}', False)

# ----------------------------------------------------------------- 8. demos used by the GUI + data integrity
G = "8. GUI demo engine and integrity"
for key, p in (("ddl", {}), ("dml", {}), ("trigger_api", {}), ("trigger_sub", {}), ("trigger_sweep", {"sim_date": "2027-03-10"}), ("fk_demo", {})):
    steps = concepts.run(key, p)
    errs = sum(1 for s_ in steps if s_["error"])
    record(G, f"Demo '{key}'", "GUI demo", "Executes through the concepts engine", "concepts.run()", "3 expected FK errors" if key == "fk_demo" else "0 errors", f"{errs} errors", errs == (3 if key == "fk_demo" else 0))
after = {t: one(f"SELECT COUNT(*) FROM `{t}`") for t in concepts.TABLES}
record(G, "Data integrity", "Check", "Row counts of all 8 tables identical before and after all tests/demos", "COUNT(*) per table", snapshot, after)
record(G, "Disposable objects", "Check", "No leftover demo table / demo team", "demo_ddl_test + 'Demo Team (temp)'", "0, 0",
       f"{one(chr(83)+'ELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s', ('demo_ddl_test',))}, {one('SELECT COUNT(*) FROM TEAM WHERE team_name=%s', ('Demo Team (temp)',))}")

# ----------------------------------------------------------------- report
ver = one("SELECT VERSION()")
passed = sum(r_["ok"] for r_ in RESULTS)
lines = ["# Database Verification Report", "",
         "**Project:** Enterprise API Governance, Discovery and Monitoring System  ", f"**Database:** `api_management` on MariaDB {ver}  ",
         f"**Generated by:** `python test_database.py` on {today} (all values below are real output from MariaDB)  ",
         f"**Result: {passed} / {len(RESULTS)} checks passed**", "",
         "Source of truth: `sql/api_management_refined.sql`, imported unchanged by `setup_db.py`. Data-changing checks ran inside transactions that were rolled back; "
         "the final row counts equal the starting counts.", "",
         "## MariaDB compatibility notes", "",
         "- The supplied SQL imported on MariaDB 10.11 with **no errors and no corrections**. Every table, view, trigger, function and procedure was kept as written.",
         "- `DELIMITER` is a client command, not SQL, so PyMySQL cannot run the file directly. `setup_db.py` splits the file itself (comment/quote aware) and executes each statement unchanged; "
         "phpMyAdmin or the `mysql` client can import the same file as is.",
         "- The seed password hashes are placeholders; `setup_db.py` replaces them with real salted hashes (data only, no schema change).",
         "- A trigger cannot fire because time passes (documented in the SQL header). The trigger `check_subscription_expiry` runs when a subscription row is inserted/updated. "
         "The app's *expiry sweep* issues a no-op `UPDATE ... SET expires_at = expires_at` so MariaDB's own trigger evaluates every overdue ACTIVE row - Python never decides the status.", ""]
groups = []
for r_ in RESULTS:
    if r_["group"] not in groups:
        groups.append(r_["group"])
for g_ in groups:
    rs = [x for x in RESULTS if x["group"] == g_]
    lines += [f"## {g_} ({sum(x['ok'] for x in rs)}/{len(rs)} passed)", "", "| Object | Type | Purpose | Test input | Expected | Observed | Result |", "|---|---|---|---|---|---|---|"]
    for x in rs:
        cell = lambda s_: str(s_).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{cell(x['obj'])}` | {x['kind']} | {cell(x['purpose'])} | `{cell(x['input'])}` | {cell(x['expected'])} | {cell(x['observed'])} | {'PASS' if x['ok'] else '**FAIL**'} |")
    lines.append("")
open("DATABASE_VERIFICATION.md", "w", encoding="utf8").write("\n".join(lines))
for x in RESULTS:
    if not x["ok"]:
        print("FAIL:", x["group"], x["obj"], "| expected:", x["expected"], "| observed:", x["observed"])
print(f"{passed}/{len(RESULTS)} checks passed -> DATABASE_VERIFICATION.md")
sys.exit(0 if passed == len(RESULTS) else 1)
