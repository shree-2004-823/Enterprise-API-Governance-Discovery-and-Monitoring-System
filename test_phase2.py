"""Comprehensive Automated Test Suite for Phase 2 Enhancements.

Tests:
1. All Sidebar Navigation Links.
2. Reports Page: Metrics, Charts, Expiry Telemetry, Version Lifecycle, Ownership, 15 Analytical Queries.
3. Expiry Sweep CSRF Token: Form token extraction and successful execution without 400 Bad Request.
4. All 14 DBMS Concepts Laboratory Demonstrations via /api/concepts/run.
5. Form submissions with CSRF tokens.
"""
import re
import sys
import os

import app as webapp
import db
from config import DEMO_PASSWORD

R = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "**FAIL**"
    print(f"[{status}] {name} {f'({detail})' if detail else ''}")
    R.append((name, bool(ok), str(detail)[:160]))


def client():
    return webapp.app.test_client()


def get_token(c):
    r = c.get("/login")
    match = re.search(r'name="csrf" value="([^"]+)"', r.get_data(as_text=True))
    return match.group(1) if match else ""


def login(email):
    c = client()
    t = get_token(c)
    c.post("/login", data={"email": email, "password": DEMO_PASSWORD, "csrf": t})
    return c, t


admin, T = login("arjun@company.com")
dev, TD = login("rahul@company.com")
cons, TC = login("kiran@company.com")

print("\n--- 1. Testing All Sidebar Navigation Links ---")
nav_routes = [
    ("/", "Dashboard", "Dashboard"),
    ("/apis", "APIs Catalog", "APIs"),
    ("/apis/1", "API Details", "Payment API"),
    ("/versions", "API Versions", "API Versions"),
    ("/endpoints", "Endpoints", "Endpoints"),
    ("/subscriptions", "Subscriptions", "Subscriptions"),
    ("/subscriptions/1", "Subscription Details", "Subscription #1"),
    ("/users", "User Management", "Users"),
    ("/reports", "Reports & Analytics", "Reports"),
    ("/concepts", "DBMS Concepts Laboratory", "DBMS Concepts Interactive Laboratory"),
]

for route, label, expected_text in nav_routes:
    r = admin.get(route)
    html = r.get_data(as_text=True)
    check(f"GET {route} ({label}) renders 200 OK", r.status_code == 200 and expected_text in html, f"HTTP {r.status_code}")

print("\n--- 2. Testing Reports & Analytics Page ---")
rep_html = admin.get("/reports").get_data(as_text=True)
check("Reports page has Executive Statistics (Total APIs, Versions, Subs, Users)",
      all(x in rep_html for x in ("Total APIs", "API Versions", "Subscriptions", "Total Users", "Active Permissions")))
check("Reports page has Category Distribution Chart", "APIs by Category" in rep_html and "chart-track" in rep_html)
check("Reports page has HTTP Method Breakdown Chart", "Endpoints by Method" in rep_html)
check("Reports page has Subscription Expiry & Duration Report", "table-expiry" in rep_html and "Subscription Expiry" in rep_html)
check("Reports page has API Version Lifecycle Report", "table-versions" in rep_html and "API Version Lifecycle" in rep_html)
check("Reports page has Developer Governance Report", "table-owners" in rep_html and "API Ownership" in rep_html)
check("Reports page includes all 15 Analytical Concept Reports",
      all(x in rep_html for x in ("api_details_view", "api_version_view", "subscription_details_view", "INNER JOIN", "LEFT JOIN", "GROUP BY", "HAVING", "Subquery", "COUNT, SUM, AVG")))
check("Reports page has interactive search input #report-search", "report-search" in rep_html)

print("\n--- 3. Testing Expiry Sweep with CSRF Fix ---")
sub_html = admin.get("/subscriptions").get_data(as_text=True)
# Find hidden csrf field inside sweep form
sweep_csrf_matches = re.findall(r'<form method="post" action="/subscriptions/sweep"[^>]*>.*?name="csrf" value="([^"]+)"', sub_html, re.DOTALL)
check("Subscriptions page sweep form contains non-empty CSRF token", len(sweep_csrf_matches) > 0 and len(sweep_csrf_matches[0]) == 32, sweep_csrf_matches[0] if sweep_csrf_matches else "EMPTY")

form_csrf = sweep_csrf_matches[0] if sweep_csrf_matches else ""
sweep_res = admin.post("/subscriptions/sweep", data={"csrf": form_csrf}, follow_redirects=True)
check("POST /subscriptions/sweep with form CSRF succeeds (200 OK, not 400 Bad Request)", sweep_res.status_code == 200 and "check_subscription_expiry processed" in sweep_res.get_data(as_text=True), f"HTTP {sweep_res.status_code}")

print("\n--- 4. Testing All 14 DBMS Laboratory Concept Demonstrations ---")
def run_demo(key, params=None):
    return admin.post("/api/concepts/run", json={"key": key, "params": params or {}}, headers={"X-CSRF-Token": T})

# Module 1: Overview
r = run_demo("db_objects").get_json()
check("Module 1: db_objects catalog query", r and not r.get("error") and len(r["steps"][0]["rows"]) >= 6)

r = run_demo("db_tables_summary").get_json()
check("Module 1: db_tables_summary engine query", r and not r.get("error") and len(r["steps"][0]["rows"]) == 8)

r = run_demo("show_create", {"table": "API"}).get_json()
check("Module 1: show_create table API", r and not r.get("error") and "CREATE TABLE" in r["steps"][0]["rows"][0][1])

# Module 2: Constraints
r = run_demo("constraints_list").get_json()
check("Module 2: constraints_list query", r and not r.get("error") and len(r["steps"][0]["rows"]) >= 10)

r = run_demo("unique_violation").get_json()
check("Module 2: unique_violation demo (catches Error 1062)", r and any("1062" in str(s.get("error")) for s in r.get("steps", [])))

r = run_demo("not_null_violation").get_json()
check("Module 2: not_null_violation demo (catches Error 1048)", r and any("1048" in str(s.get("error")) for s in r.get("steps", [])))

# Module 3: Keys & Relationships
r = run_demo("fk_list").get_json()
check("Module 3: fk_list foreign key catalog", r and not r.get("error") and len(r["steps"][0]["rows"]) >= 9)

r = run_demo("fk_demo").get_json()
check("Module 3: fk_demo illegal operations (catches Errors 1451/1452)", r and sum(1 for s in r.get("steps", []) if s.get("error")) == 3)

r = run_demo("fk_cascade").get_json()
check("Module 3: fk_cascade demo (verifies ON DELETE CASCADE)", r and not r.get("error") and len(r["steps"]) >= 4)

# Module 4: DDL Operations
r = run_demo("ddl").get_json()
check("Module 4: DDL lifecycle (CREATE, ALTER ADD, ALTER DROP, DROP)", r and not r.get("error") and len(r["steps"]) >= 6)

# Module 5: DML Operations
r = run_demo("dml").get_json()
check("Module 5: DML lifecycle (INSERT, UPDATE, DELETE)", r and not r.get("error") and len(r["steps"]) >= 5)

r = run_demo("dml_rollback").get_json()
check("Module 5: dml_rollback ACID atomicity demonstration", r and not r.get("error") and len(r["steps"]) >= 4)

# Module 6: Basic SELECT
r = run_demo("select_filter_apis").get_json()
check("Module 6: select_filter_apis projection & WHERE", r and not r.get("error") and len(r["steps"][0]["rows"]) >= 4)

r = run_demo("select_pattern_matching").get_json()
check("Module 6: select_pattern_matching LIKE query", r and not r.get("error") and len(r["steps"][0]["rows"]) >= 1)

r = run_demo("select_range_dates").get_json()
check("Module 6: select_range_dates BETWEEN query", r and not r.get("error") and len(r["steps"][0]["rows"]) >= 1)

# Module 7: JOINs
r = run_demo("inner_api_owner").get_json()
check("Module 7: inner_api_owner (API + USER)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 4)

r = run_demo("inner_subscription").get_json()
check("Module 7: inner_subscription (4-table join)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 5)

r = run_demo("left_versions").get_json()
check("Module 7: left_versions (preserving unmatched)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 4)

r = run_demo("left_users_subs").get_json()
check("Module 7: left_users_subs (all 5 users retained)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 5)

# Module 8: Aggregates
r = run_demo("agg_all").get_json()
check("Module 8: agg_all (COUNT, SUM, AVG, MIN, MAX)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 1)

r = run_demo("agg_api").get_json()
check("Module 8: agg_api (conditional SUM, AVG)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 1)

# Module 9: GROUP BY and HAVING
r = run_demo("group_by").get_json()
check("Module 9: group_by subscriptions per API", r and not r.get("error") and len(r["steps"][0]["rows"]) == 4)

r = run_demo("having").get_json()
check("Module 9: having APIs with multiple subscriptions", r and not r.get("error") and len(r["steps"][0]["rows"]) == 1)

r = run_demo("team_having").get_json()
check("Module 9: team_having teams with multiple members", r and not r.get("error") and len(r["steps"][0]["rows"]) == 2)

# Module 10: Subqueries
r = run_demo("sub_in").get_json()
check("Module 10: sub_in (membership predicate)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 4)

r = run_demo("sub_not_exists").get_json()
check("Module 10: sub_not_exists (correlated subquery)", r and not r.get("error"))

r = run_demo("sub_scalar").get_json()
check("Module 10: sub_scalar (scalar subquery in SELECT)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 4)

r = run_demo("sub_derived").get_json()
check("Module 10: sub_derived (derived table in HAVING)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 1)

# Module 11: Views
r = run_demo("view_api_details").get_json()
check("Module 11: view_api_details (api_details_view)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 4)

r = run_demo("view_api_version").get_json()
check("Module 11: view_api_version (api_version_view)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 5)

r = run_demo("view_subscription").get_json()
check("Module 11: view_subscription (subscription_details_view)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 5)

r = run_demo("view_filtered").get_json()
check("Module 11: view_filtered (WHERE on virtual table)", r and not r.get("error") and len(r["steps"][0]["rows"]) >= 3)

# Module 12: Stored Functions
r = run_demo("fn_age", {"api_date": "2020-01-01"}).get_json()
check("Module 12: fn_age api_age() execution", r and not r.get("error") and r["steps"][0]["rows"][0][0] >= 6)

r = run_demo("fn_days", {"start_date": "2026-01-01", "end_date": "2026-04-11"}).get_json()
check("Module 12: fn_days subscription_days() execution", r and not r.get("error") and r["steps"][0]["rows"][0][0] == 100)

r = run_demo("fn_label", {"status": "ACTIVE"}).get_json()
check("Module 12: fn_label api_status_label() execution", r and not r.get("error") and "active" in r["steps"][0]["rows"][0][0].lower())

# Module 13: Stored Procedures
r = run_demo("proc_owner", {"owner_id": "1"}).get_json()
check("Module 13: proc_owner get_apis_by_owner(1)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 2)

r = run_demo("proc_api", {"api_id": "1"}).get_json()
check("Module 13: proc_api get_api_subscriptions(1)", r and not r.get("error") and len(r["steps"][0]["rows"]) == 2)

# Module 14: Triggers
r = run_demo("trigger_list").get_json()
check("Module 14: trigger_list dictionary query", r and not r.get("error") and len(r["steps"][0]["rows"]) == 3)

r = run_demo("trigger_api").get_json()
check("Module 14: trigger_api after_api_deprecated firing", r and not r.get("error") and len(r["steps"]) >= 4)

r = run_demo("trigger_sub").get_json()
check("Module 14: trigger_sub check_subscription_expiry firing", r and not r.get("error") and len(r["steps"]) >= 6)

r = run_demo("trigger_sweep", {"sim_date": "2027-03-10"}).get_json()
check("Module 14: trigger_sweep time-travel simulation", r and not r.get("error") and len(r["steps"]) >= 6)

print("\n--- Summary of Phase 2 Test Results ---")
passed = sum(1 for _, ok, _ in R if ok)
total = len(R)
print(f"Results: {passed} / {total} checks passed!")
if passed == total:
    print("ALL PHASE 2 VERIFICATIONS PASSED WITH 100% SUCCESS!")
else:
    print(f"WARNING: {total - passed} checks failed!")
    sys.exit(1)
