"""Reports and Analytics Data Engine.

Fetches live statistics, aggregations, and grouped metrics from MySQL
for the Executive & Operational Reports Dashboard.
"""
import db
import concepts


def get_reports_data():
    # 1. Comprehensive Overview Statistics
    overview = db.query("""
        SELECT 
            (SELECT COUNT(*) FROM API) AS total_apis,
            (SELECT COUNT(*) FROM API WHERE status='ACTIVE') AS active_apis,
            (SELECT COUNT(*) FROM API WHERE status='DEPRECATED') AS deprecated_apis,
            (SELECT COUNT(*) FROM API WHERE status='MAINTENANCE') AS maintenance_apis,
            (SELECT COUNT(*) FROM API WHERE status='INACTIVE') AS inactive_apis,
            (SELECT COUNT(*) FROM API_VERSION) AS total_versions,
            (SELECT COUNT(*) FROM API_VERSION WHERE status='ACTIVE') AS active_versions,
            (SELECT COUNT(*) FROM API_VERSION WHERE status='DEPRECATED') AS deprecated_versions,
            (SELECT COUNT(*) FROM ENDPOINT) AS total_endpoints,
            (SELECT COUNT(*) FROM SUBSCRIPTION) AS total_subs,
            (SELECT COUNT(*) FROM SUBSCRIPTION WHERE status='ACTIVE') AS active_subs,
            (SELECT COUNT(*) FROM SUBSCRIPTION WHERE status='EXPIRED') AS expired_subs,
            (SELECT COUNT(*) FROM `USER`) AS total_users,
            (SELECT COUNT(*) FROM `ROLE`) AS total_roles,
            (SELECT COUNT(*) FROM TEAM) AS total_teams,
            (SELECT COUNT(*) FROM PERMISSION) AS total_permissions
    """, one=True) or {}

    # 2. APIs Grouped by Category
    categories = db.query("""
        SELECT 
            COALESCE(category, 'Uncategorized') AS category,
            COUNT(*) AS total_apis,
            SUM(status = 'ACTIVE') AS active_apis,
            SUM(status = 'DEPRECATED') AS deprecated_apis,
            SUM(status = 'MAINTENANCE') AS maintenance_apis
        FROM API
        GROUP BY category
        ORDER BY total_apis DESC, category ASC
    """)
    total_apis = overview.get("total_apis") or 1
    for c in categories:
        c["percentage"] = round((c["total_apis"] / total_apis) * 100, 1)

    # 3. APIs Grouped by Owner
    owners = db.query("""
        SELECT 
            U.user_id,
            U.full_name,
            U.email,
            R.role_name,
            T.team_name,
            COUNT(A.api_id) AS owned_apis,
            SUM(CASE WHEN A.status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_apis,
            SUM(CASE WHEN A.status = 'DEPRECATED' THEN 1 ELSE 0 END) AS deprecated_apis
        FROM `USER` U
        JOIN `ROLE` R ON U.role_id = R.role_id
        JOIN TEAM T ON U.team_id = T.team_id
        LEFT JOIN API A ON A.owner_id = U.user_id
        GROUP BY U.user_id, U.full_name, U.email, R.role_name, T.team_name
        ORDER BY owned_apis DESC, U.full_name ASC
    """)

    # 4. API Versions Detailed Report
    versions = db.query("""
        SELECT 
            V.version_id,
            A.api_name,
            A.category,
            V.version_number,
            V.release_date,
            V.status,
            V.deprecated_date,
            api_age(V.release_date) AS age_years,
            (SELECT COUNT(*) FROM ENDPOINT E WHERE E.version_id = V.version_id) AS endpoints_count,
            (SELECT COUNT(*) FROM SUBSCRIPTION S WHERE S.version_id = V.version_id) AS subscriptions_count
        FROM API_VERSION V
        JOIN API A ON V.api_id = A.api_id
        ORDER BY A.api_name ASC, V.version_number ASC
    """)

    # 5. Subscription Expiry & Duration Report
    expiry_report = db.query("""
        SELECT 
            S.subscription_id,
            U.full_name AS consumer_name,
            U.email AS consumer_email,
            A.api_name,
            V.version_number,
            S.status,
            S.subscribe_date,
            S.expires_at,
            subscription_days(S.subscribe_date, S.expires_at) AS duration_days,
            DATEDIFF(S.expires_at, CURDATE()) AS days_left
        FROM SUBSCRIPTION S
        JOIN `USER` U ON S.consumer_id = U.user_id
        JOIN API A ON S.api_id = A.api_id
        JOIN API_VERSION V ON S.version_id = V.version_id AND S.api_id = V.api_id
        ORDER BY S.expires_at ASC, S.subscription_id ASC
    """)
    for s in expiry_report:
        days = s.get("days_left")
        if s.get("status") == "EXPIRED" or (days is not None and days < 0):
            s["urgency"] = "expired"
        elif days is not None and days <= 30:
            s["urgency"] = "critical"
        elif days is not None and days <= 90:
            s["urgency"] = "warning"
        else:
            s["urgency"] = "healthy"

    # 6. Users Grouped by Role
    roles = db.query("""
        SELECT 
            R.role_id,
            R.role_name,
            R.description,
            COUNT(U.user_id) AS user_count
        FROM `ROLE` R
        LEFT JOIN `USER` U ON R.role_id = U.role_id
        GROUP BY R.role_id, R.role_name, R.description
        ORDER BY user_count DESC
    """)
    total_users = overview.get("total_users") or 1
    for r in roles:
        r["percentage"] = round((r["user_count"] / total_users) * 100, 1)

    # 7. Endpoints Breakdown by Method
    methods = db.query("""
        SELECT 
            method,
            COUNT(*) AS count
        FROM ENDPOINT
        GROUP BY method
        ORDER BY count DESC
    """)
    total_endpoints = overview.get("total_endpoints") or 1
    for m in methods:
        m["percentage"] = round((m["count"] / total_endpoints) * 100, 1)

    # 8. Standard Academic Query Reports (from concepts engine)
    sql_reports = [concepts.run_query(k) for k in concepts.REPORT_ORDER]

    return {
        "overview": overview,
        "categories": categories,
        "owners": owners,
        "versions": versions,
        "expiry_report": expiry_report,
        "roles": roles,
        "methods": methods,
        "sql_reports": sql_reports,
    }
