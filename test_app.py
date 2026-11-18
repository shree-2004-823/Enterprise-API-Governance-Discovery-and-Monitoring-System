"""End-to-end test of the Flask GUI against the real MariaDB. Writes APPLICATION_TEST_REPORT.md.

    python test_app.py

Creates temporary test rows THROUGH THE GUI and removes them again through the GUI.
"""
import re
import sys

import app as webapp
import db
from config import DEMO_PASSWORD

R = []


def check(name, ok, detail=""):
    R.append((name, bool(ok), str(detail)[:160]))


def client():
    return webapp.app.test_client()


def token(c):
    c.get("/login")
    with c.session_transaction() as s:
        return s["csrf"]


def login(email):
    c = client()
    t = token(c)
    c.post("/login", data={"email": email, "password": DEMO_PASSWORD, "csrf": t})
    return c, t


def q(sql, a=None):
    conn = db.connect(dict_rows=False)
    try:
        cur = conn.cursor()
        cur.execute(sql, a)
        return db.clean_rows(cur.fetchall())
    finally:
        conn.close()


admin, T = login("arjun@company.com")
dev, TD = login("rahul@company.com")
cons, TC = login("kiran@company.com")

# ---- authentication
c0 = client()
check("Anonymous user is redirected to /login", c0.get("/apis").status_code == 302)
t0 = token(c0)
r = c0.post("/login", data={"email": "arjun@company.com", "password": "wrong", "csrf": t0})
check("Wrong password rejected", b"Invalid email or password" in r.data)
check("POST without CSRF token is refused (400)", client().post("/login", data={"email": "a", "password": "b"}).status_code == 400)

# ---- every page renders
pages = ["/", "/apis", "/apis/1", "/versions", "/endpoints", "/subscriptions", "/subscriptions/1", "/users", "/reports", "/concepts"]
for p in pages:
    r = admin.get(p)
    check(f"GET {p} renders (200)", r.status_code == 200, r.status_code)
check("Consumer cannot open /users", cons.get("/users").status_code == 302)

# ---- views / functions visible in pages
r = admin.get("/apis").get_data(as_text=True)
check("APIs page lists all 4 APIs from api_details_view with api_age() column", all(n in r for n in ("Payment API", "Notification API", "Product API", "User Authentication API")) and "api_age()" in r)
r = admin.get("/subscriptions").get_data(as_text=True)
check("Subscriptions page shows subscription_days() duration (365)", "subscription_days()" in r and ">365<" in r)
r = admin.get("/reports").get_data(as_text=True)
check("Reports page shows view + join + aggregate results", all(x in r for x in ("api_details_view", "HAVING", "Rahul Sharma", "1825")))

# ---- stored procedures through the GUI endpoint
def run(c, tok, key, params=None):
    return c.post("/api/concepts/run", json={"key": key, "params": params or {}}, headers={"X-CSRF-Token": tok})


r = run(admin, T, "proc_owner", {"owner_id": "1"}).get_json()
names = [x[1] for x in r["steps"][0]["rows"]]
check("Procedure get_apis_by_owner(1) via GUI endpoint", names == ["Notification API", "User Authentication API"], names)
r = run(admin, T, "proc_api", {"api_id": "1"}).get_json()
check("Procedure get_api_subscriptions(1) via GUI endpoint", [x[1] for x in r["steps"][0]["rows"]] == ["Sneha Patel", "Kiran Rao"], r["steps"][0]["rows"])
check("API detail page shows procedure result (CALL get_api_subscriptions)", "Sneha Patel" in admin.get("/apis/1").get_data(as_text=True))

# ---- GUI trigger #1: deprecate an API through the GUI, MariaDB trigger updates versions
admin.post("/apis/add", data={"api_name": "GUI_TEST_API", "category": "Test", "owner_id": "2", "status": "ACTIVE", "description": "temp", "csrf": T})
aid = q("SELECT api_id FROM API WHERE api_name='GUI_TEST_API'")[0][0]
check("API created through GUI", aid > 0, aid)
for v in ("v1", "v2"):
    admin.post("/versions/add", data={"api_id": aid, "version_number": v, "release_date": "2026-01-01", "status": "ACTIVE", "csrf": T})
before = q("SELECT status FROM API_VERSION WHERE api_id=%s", (aid,))
check("Test versions start ACTIVE", before == [["ACTIVE"], ["ACTIVE"]], before)
r = admin.post(f"/apis/{aid}/status", data={"status": "DEPRECATED", "csrf": T}, follow_redirects=True).get_data(as_text=True)
after = q("SELECT status, deprecated_date IS NOT NULL FROM API_VERSION WHERE api_id=%s", (aid,))
check("GUI status change -> TRIGGER after_api_deprecated deprecated the versions", after == [["DEPRECATED", 1], ["DEPRECATED", 1]], after)
check("GUI shows the trigger message", "after_api_deprecated fired inside MariaDB" in r)

# ---- GUI trigger #2: subscription expiry through the GUI
admin.post("/subscriptions/add", data={"api_id": 1, "version_id": 2, "consumer_id": 4, "status": "ACTIVE", "subscribe_date": "2026-01-01", "expires_at": "2026-02-01", "csrf": T})
sid = q("SELECT MAX(subscription_id) FROM SUBSCRIPTION")[0][0]
st = q("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (sid,))[0][0]
check("GUI insert of ACTIVE subscription with past expiry -> stored EXPIRED by trigger", st == "EXPIRED", st)
admin.post(f"/subscriptions/{sid}/update", data={"status": "ACTIVE", "expires_at": "2099-01-01", "csrf": T})
check("Valid future expiry keeps ACTIVE", q("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (sid,))[0][0] == "ACTIVE")
r = admin.post(f"/subscriptions/{sid}/update", data={"status": "ACTIVE", "expires_at": "2020-01-01", "csrf": T}, follow_redirects=True).get_data(as_text=True)
check("GUI update to past expiry -> trigger sets EXPIRED and GUI reports it", q("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (sid,))[0][0] == "EXPIRED" and "check_subscription_expiry changed" in r)
r = admin.post("/subscriptions/sweep", data={"csrf": T}, follow_redirects=True).get_data(as_text=True)
check("Expiry sweep button runs (0 overdue ACTIVE rows today)", "processed 0 overdue" in r, re.findall(r"processed \d+ overdue", r))

# ---- foreign keys through the GUI
r = admin.post("/apis/add", data={"api_name": "FK_FAIL", "owner_id": "999", "status": "ACTIVE", "csrf": T}, follow_redirects=True).get_data(as_text=True)
check("GUI shows MariaDB FK error 1452 for unknown owner", "error 1452" in r and not q("SELECT 1 FROM API WHERE api_name='FK_FAIL'"))
r = admin.post("/apis/1/delete", data={"csrf": T}, follow_redirects=True).get_data(as_text=True)
check("GUI shows MariaDB FK error 1451 deleting an API that has subscriptions", "error 1451" in r and q("SELECT 1 FROM API WHERE api_id=1"))
r = admin.post("/subscriptions/add", data={"api_id": 1, "version_id": 3, "consumer_id": 4, "status": "ACTIVE", "subscribe_date": "2026-01-01", "csrf": T}, follow_redirects=True).get_data(as_text=True)
check("Composite FK rejects version of another API", "error 1452" in r)

# ---- role-based access
r = cons.post("/apis/add", data={"api_name": "CONSUMER_API", "owner_id": "2", "csrf": TC}, follow_redirects=True).get_data(as_text=True)
check("Consumer is read-only (cannot create API)", "read-only" in r and not q("SELECT 1 FROM API WHERE api_name='CONSUMER_API'"))
check("Consumer cannot run data-changing demo (403)", run(cons, TC, "trigger_api").status_code == 403)
check("Consumer can run read-only demo", run(cons, TC, "inner_api_owner").status_code == 200)

# ---- DBMS Concepts page
page = admin.get("/concepts").get_data(as_text=True)
for title in ("1. Tables and Relationships", "2. DDL Operations", "3. DML Operations", "4. JOIN Queries", "5. Subqueries", "6. Aggregate Functions",
              "7. Database Views", "8. Triggers", "9. Stored Functions", "10. Stored Procedures"):
    check(f"Concepts page has section '{title}'", title in page)
check("Concepts page shows live trigger/function/procedure/view definitions from MariaDB",
      all(x in page for x in ("CREATE DEFINER", "TRIGGER after_api_deprecated", "FUNCTION `api_age`", "PROCEDURE `get_apis_by_owner`", "api_details_view")))
for key, p in [("trigger_api", {}), ("trigger_sub", {}), ("trigger_sweep", {"sim_date": "2027-03-10"}), ("fn_age", {"api_date": "2020-06-15"}),
               ("fn_days", {"start_date": "2026-03-01", "end_date": "2027-03-01"}), ("fn_label", {"status": "ACTIVE"}), ("ddl", {}), ("dml", {}), ("fk_demo", {}),
               ("show_create", {"table": "API"}), ("view_api_details", {}), ("view_api_version", {}), ("having", {}), ("sub_derived", {})]:
    r = run(admin, T, key, p)
    steps = r.get_json().get("steps", [])
    bad = [s for s in steps if s["error"]] if key != "fk_demo" else []
    check(f"Concepts demo '{key}' runs (200, no MariaDB errors)", r.status_code == 200 and steps and not bad, r.status_code)
r = run(admin, T, "trigger_sweep", {"sim_date": "2027-03-10"}).get_json()["steps"]
check("Time-travel sweep AFTER shows subscriptions 1-3 EXPIRED", [x[1] for x in r[4]["rows"]][:3] == ["EXPIRED"] * 3, r[4]["rows"])
r = run(admin, T, "fn_age", {"api_date": "2020-06-15"}).get_json()["steps"][0]["rows"][0]
check("api_age('2020-06-15') through GUI = 6 (CURDATE 2026-11-17)", r[0] == 6, r)

# ---- safety: no arbitrary SQL from the browser
check("Unknown demo key / raw SQL is refused", run(admin, T, "DROP TABLE API").status_code == 400)
check("SQL injection in procedure parameter refused", run(admin, T, "proc_owner", {"owner_id": "1; DROP TABLE API"}).status_code == 400)
check("SQL injection in table name refused", run(admin, T, "table", {"table": "API; DROP TABLE API"}).status_code == 400)
check("SQL injection via function date refused", run(admin, T, "fn_age", {"api_date": "2020-01-01'); DROP TABLE API;--"}).status_code == 400)
check("Run endpoint needs CSRF header", admin.post("/api/concepts/run", json={"key": "fk_list"}).status_code == 400)
check("API table still exists after injection attempts", q("SELECT COUNT(*) FROM API")[0][0] >= 4)

# ---- clean up through the GUI
admin.post(f"/subscriptions/{sid}/delete", data={"csrf": T})
admin.post(f"/apis/{aid}/delete", data={"csrf": T})
check("Clean-up via GUI: test subscription and API removed",
      not q("SELECT 1 FROM SUBSCRIPTION WHERE subscription_id=%s", (sid,)) and not q("SELECT 1 FROM API WHERE api_id=%s", (aid,)))
check("Clean-up: cascade removed the test versions", not q("SELECT 1 FROM API_VERSION WHERE api_id=%s", (aid,)))

ok = sum(1 for _, o, _ in R if o)
md = ["# Application (GUI) Test Report", "", f"**Result: {ok} / {len(R)} checks passed**  ", "Run with `python test_app.py` against the real MariaDB database.", "",
      "| # | Check | Result | Detail |", "|---|---|---|---|"]
md += [f"| {i} | {n} | {'PASS' if o else '**FAIL**'} | {d.replace('|', '/')} |" for i, (n, o, d) in enumerate(R, 1)]
open("APPLICATION_TEST_REPORT.md", "w", encoding="utf8").write("\n".join(md))
for n, o, d in R:
    if not o:
        print("FAIL:", n, "|", d)
print(f"{ok}/{len(R)} GUI checks passed -> APPLICATION_TEST_REPORT.md")
sys.exit(0 if ok == len(R) else 1)
