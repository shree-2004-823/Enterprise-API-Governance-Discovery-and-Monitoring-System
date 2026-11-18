"""Enterprise API Governance, Discovery and Monitoring System - Flask front end.

Flask only sends SQL to MariaDB and shows what MariaDB returns. Triggers, stored
functions, stored procedures and views are the database's own objects (see sql/).
"""
import functools
import secrets

import pymysql
from flask import (Flask, abort, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import concepts
import db
import reports_data
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.teardown_appcontext(db.close_db)

# Ensure csrf_token is available globally in all Jinja templates and imported macros
app.jinja_env.globals["csrf_token"] = lambda: session.get("csrf", "")

API_STATUSES = ["ACTIVE", "DEPRECATED", "MAINTENANCE", "INACTIVE"]
VERSION_STATUSES = ["ACTIVE", "DEPRECATED"]
SUB_STATUSES = ["ACTIVE", "EXPIRED", "CANCELLED", "SUSPENDED"]
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


# ------------------------------------------------------------------ security helpers
@app.before_request
def csrf_protect():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        token = request.form.get("csrf") or request.headers.get("X-CSRF-Token")
        if not token or token != session.get("csrf"):
            abort(400, "Invalid CSRF token")


@app.context_processor
def inject():
    return dict(csrf=session.get("csrf", ""), me=session.get("user"), can_write=can_write(),
                is_admin=session.get("user", {}).get("role") == "Admin")


def can_write():
    return session.get("user", {}).get("role") in ("Admin", "Developer")


def login_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        if "user" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*a, **k)
    return w


def write_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        if not can_write():
            flash("Your role has read-only access.", "error")
            return redirect(request.referrer or url_for("dashboard"))
        return f(*a, **k)
    return login_required(w)


def admin_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        if session.get("user", {}).get("role") != "Admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return f(*a, **k)
    return login_required(w)


def attempt(sql, args, ok_msg):
    """Run a write. MariaDB constraint errors are shown to the user (great for FK demos)."""
    try:
        n, last = db.execute(sql, args)
        flash(ok_msg, "ok")
        return n, last
    except pymysql.MySQLError as e:
        flash(f"MariaDB rejected the operation (error {e.args[0]}): {e.args[1]}", "error")
        return None, None


def val(name, default=None):
    v = request.form.get(name, "").strip()
    return v if v else default


# ------------------------------------------------------------------ auth
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db.query("SELECT U.user_id, U.full_name, U.email, U.password_hash, U.status, R.role_name "
                     "FROM `USER` U JOIN `ROLE` R ON U.role_id = R.role_id WHERE U.email = %s",
                     (request.form.get("email", "").strip(),), one=True)
        if u and u["status"] == "ACTIVE" and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session["user"] = dict(id=u["user_id"], name=u["full_name"], role=u["role_name"])
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ------------------------------------------------------------------ dashboard
@app.route("/")
@login_required
def dashboard():
    stats = db.query("SELECT (SELECT COUNT(*) FROM API) AS apis, (SELECT COUNT(*) FROM API_VERSION) AS versions, "
                     "(SELECT COUNT(*) FROM ENDPOINT) AS endpoints, "
                     "(SELECT COUNT(*) FROM SUBSCRIPTION WHERE status='ACTIVE') AS active_subs, "
                     "(SELECT COUNT(*) FROM `USER`) AS users", one=True)
    by_status = db.query("SELECT status, COUNT(*) AS total FROM API GROUP BY status ORDER BY status")
    recent = db.query("SELECT api_name, version_number, status, release_date FROM api_version_view "
                      "ORDER BY release_date DESC, version_id DESC LIMIT 5")
    objects = db.query("SELECT (SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()) AS triggers_n, "
                       "(SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() AND ROUTINE_TYPE='FUNCTION') AS functions_n, "
                       "(SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() AND ROUTINE_TYPE='PROCEDURE') AS procedures_n, "
                       "(SELECT COUNT(*) FROM information_schema.VIEWS WHERE TABLE_SCHEMA=DATABASE()) AS views_n", one=True)
    return render_template("dashboard.html", stats=stats, by_status=by_status, recent=recent, objects=objects)


# ------------------------------------------------------------------ APIs
API_LIST_SQL = """SELECT d.api_id, d.api_name, d.category, d.status, d.owner_name, d.created_at,
       api_age(DATE(d.created_at)) AS age_years,
       api_status_label(d.status) AS status_label,
       (SELECT COUNT(*) FROM API_VERSION v WHERE v.api_id = d.api_id) AS versions
FROM api_details_view d ORDER BY d.api_id"""


def owners():
    return db.query("SELECT U.user_id, U.full_name, R.role_name FROM `USER` U JOIN `ROLE` R ON U.role_id=R.role_id "
                    "ORDER BY U.full_name")


@app.route("/apis")
@login_required
def apis():
    return render_template("apis.html", apis=db.query(API_LIST_SQL), owners=owners(), statuses=API_STATUSES,
                           owner_opts=dropdown_sources()["owners"])


@app.post("/apis/add")
@write_required
def api_add():
    attempt("INSERT INTO API (api_name, description, category, status, owner_id) VALUES (%s,%s,%s,%s,%s)",
            (val("api_name"), val("description"), val("category"), val("status", "ACTIVE"), val("owner_id")),
            "API created.")
    return redirect(url_for("apis"))


@app.route("/apis/<int:api_id>")
@login_required
def api_detail(api_id):
    api = db.query("SELECT d.*, api_age(DATE(d.created_at)) AS age_years, api_status_label(d.status) AS status_label "
                   "FROM api_details_view d WHERE d.api_id=%s", (api_id,), one=True)
    if not api:
        abort(404)
    versions = db.query("SELECT * FROM api_version_view WHERE api_id=%s ORDER BY version_id", (api_id,))
    endpoints = db.query("SELECT V.version_number, E.method, E.endpoint_path, E.description FROM ENDPOINT E "
                         "JOIN API_VERSION V ON E.version_id=V.version_id WHERE V.api_id=%s ORDER BY V.version_id, E.endpoint_id", (api_id,))
    subs = db.call_proc("get_api_subscriptions", (api_id,))
    return render_template("api_detail.html", api=api, versions=versions, endpoints=endpoints,
                           subs=subs[0] if subs else {"columns": [], "rows": []},
                           owners=owners(), statuses=API_STATUSES)


@app.post("/apis/<int:api_id>/edit")
@write_required
def api_edit(api_id):
    attempt("UPDATE API SET api_name=%s, description=%s, category=%s, owner_id=%s WHERE api_id=%s",
            (val("api_name"), val("description"), val("category"), val("owner_id"), api_id), "API updated.")
    return redirect(url_for("api_detail", api_id=api_id))


@app.post("/apis/<int:api_id>/status")
@write_required
def api_status(api_id):
    new = val("status")
    if new not in API_STATUSES:
        abort(400)
    ver_sql = "SELECT version_id, version_number, status FROM API_VERSION WHERE api_id=%s ORDER BY version_id"
    before = {v["version_id"]: v for v in db.query(ver_sql, (api_id,))}
    n, _ = attempt("UPDATE API SET status=%s WHERE api_id=%s", (new, api_id), f"API status set to {new}.")
    if n is not None:
        after = db.query(ver_sql, (api_id,))
        changed = [f"{v['version_number']} ({before[v['version_id']]['status']} -> {v['status']})"
                   for v in after if before[v["version_id"]]["status"] != v["status"]]
        if changed:
            flash("TRIGGER after_api_deprecated fired inside MariaDB and changed: " + ", ".join(changed), "trigger")
        elif new == "DEPRECATED":
            flash("Trigger fired but there were no ACTIVE versions left to change.", "trigger")
    return redirect(url_for("api_detail", api_id=api_id))


@app.post("/apis/<int:api_id>/delete")
@write_required
def api_delete(api_id):
    n, _ = attempt("DELETE FROM API WHERE api_id=%s", (api_id,), "API deleted (its versions and endpoints cascade).")
    return redirect(url_for("apis" if n is not None else "api_detail", api_id=api_id))


# ------------------------------------------------------------------ versions / endpoints
@app.route("/versions")
@login_required
def versions():
    rows = db.query("SELECT v.*, (SELECT COUNT(*) FROM ENDPOINT e WHERE e.version_id=v.version_id) AS endpoints, "
                    "api_age(v.release_date) AS age_years FROM api_version_view v ORDER BY v.api_id, v.version_id")
    return render_template("versions.html", rows=rows, apis=db.query("SELECT api_id, api_name FROM API ORDER BY api_name"),
                           statuses=VERSION_STATUSES)


@app.post("/versions/add")
@write_required
def version_add():
    attempt("INSERT INTO API_VERSION (api_id, version_number, release_date, status, changelog) VALUES (%s,%s,%s,%s,%s)",
            (val("api_id"), val("version_number"), val("release_date"), val("status", "ACTIVE"), val("changelog")),
            "Version created.")
    return redirect(url_for("versions"))


@app.post("/versions/<int:vid>/status")
@write_required
def version_status(vid):
    st = val("status")
    if st not in VERSION_STATUSES:
        abort(400)
    attempt("UPDATE API_VERSION SET status=%s, deprecated_date = IF(%s='DEPRECATED', COALESCE(deprecated_date, CURDATE()), NULL) "
            "WHERE version_id=%s", (st, st, vid), "Version status updated.")
    return redirect(url_for("versions"))


@app.post("/versions/<int:vid>/delete")
@write_required
def version_delete(vid):
    attempt("DELETE FROM API_VERSION WHERE version_id=%s", (vid,),
            "Version deleted (endpoints cascade).")
    return redirect(url_for("versions"))


@app.route("/endpoints")
@login_required
def endpoints():
    rows = db.query("SELECT E.endpoint_id, A.api_name, V.version_number, E.method, E.endpoint_path, E.description "
                    "FROM ENDPOINT E JOIN API_VERSION V ON E.version_id=V.version_id JOIN API A ON V.api_id=A.api_id "
                    "ORDER BY A.api_name, V.version_number, E.endpoint_id")
    vers = db.query("SELECT version_id, api_name, version_number FROM api_version_view ORDER BY api_name, version_number")
    return render_template("endpoints.html", rows=rows, versions=vers, methods=METHODS)


@app.post("/endpoints/add")
@write_required
def endpoint_add():
    attempt("INSERT INTO ENDPOINT (version_id, method, endpoint_path, description) VALUES (%s,%s,%s,%s)",
            (val("version_id"), val("method"), val("endpoint_path"), val("description")), "Endpoint created.")
    return redirect(url_for("endpoints"))


@app.post("/endpoints/<int:eid>/delete")
@write_required
def endpoint_delete(eid):
    attempt("DELETE FROM ENDPOINT WHERE endpoint_id=%s", (eid,), "Endpoint deleted.")
    return redirect(url_for("endpoints"))


# ------------------------------------------------------------------ subscriptions
@app.route("/subscriptions")
@login_required
def subscriptions():
    rows = db.query("""SELECT v.*, subscription_days(v.subscribe_date, v.expires_at) AS duration_days,
                              DATEDIFF(v.expires_at, CURDATE()) AS days_left,
                              (SELECT COUNT(*) FROM PERMISSION p WHERE p.subscription_id = v.subscription_id) AS permissions
                       FROM subscription_details_view v ORDER BY v.subscription_id""")
    return render_template("subscriptions.html", rows=rows,
                           apis=db.query("SELECT api_id, api_name FROM API ORDER BY api_name"),
                           versions=db.query("SELECT version_id, api_id, version_number FROM API_VERSION ORDER BY api_id, version_number"),
                           consumers=owners(), statuses=SUB_STATUSES, api_opts=dropdown_sources()["apis"])


@app.post("/subscriptions/add")
@write_required
def subscription_add():
    attempt("INSERT INTO SUBSCRIPTION (api_id, version_id, consumer_id, status, subscribe_date, expires_at) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (val("api_id"), val("version_id"), val("consumer_id"), val("status", "ACTIVE"),
             val("subscribe_date"), val("expires_at")), "Subscription created.")
    return redirect(url_for("subscriptions"))


@app.post("/subscriptions/sweep")
@write_required
def subscription_sweep():
    # Touches each stale ACTIVE row; the BEFORE UPDATE trigger decides the new status.
    n, _ = attempt("UPDATE SUBSCRIPTION SET expires_at = expires_at WHERE status = 'ACTIVE' AND expires_at < CURDATE()",
                   None, "Expiry sweep executed.")
    if n is not None:
        flash(f"TRIGGER check_subscription_expiry processed {n} overdue subscription(s) inside MariaDB.", "trigger")
    return redirect(url_for("subscriptions"))


@app.post("/subscriptions/<int:sid>/update")
@write_required
def subscription_update(sid):
    before = db.query("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (sid,), one=True)
    n, _ = attempt("UPDATE SUBSCRIPTION SET status=%s, expires_at=%s WHERE subscription_id=%s",
                   (val("status"), val("expires_at"), sid), "Subscription updated.")
    after = db.query("SELECT status FROM SUBSCRIPTION WHERE subscription_id=%s", (sid,), one=True)
    if n is not None and before and after and after["status"] != val("status"):
        flash(f"TRIGGER check_subscription_expiry changed the status you chose ({val('status')}) to {after['status']}: "
              f"the expiry date is in the past.", "trigger")
    return redirect(request.referrer or url_for("subscriptions"))


@app.post("/subscriptions/<int:sid>/delete")
@write_required
def subscription_delete(sid):
    attempt("DELETE FROM SUBSCRIPTION WHERE subscription_id=%s", (sid,), "Subscription deleted (permissions cascade).")
    return redirect(url_for("subscriptions"))


@app.route("/subscriptions/<int:sid>")
@login_required
def subscription_detail(sid):
    s = db.query("SELECT v.*, subscription_days(v.subscribe_date, v.expires_at) AS duration_days "
                 "FROM subscription_details_view v WHERE v.subscription_id=%s", (sid,), one=True)
    if not s:
        abort(404)
    perms = db.query("SELECT * FROM PERMISSION WHERE subscription_id=%s ORDER BY permission_id", (sid,))
    return render_template("subscription_detail.html", s=s, perms=perms, statuses=SUB_STATUSES)


@app.post("/subscriptions/<int:sid>/permissions/add")
@write_required
def permission_add(sid):
    attempt("INSERT INTO PERMISSION (subscription_id, permission_type, allowed) VALUES (%s,%s,%s)",
            (sid, val("permission_type"), 1 if val("allowed") == "1" else 0), "Permission added.")
    return redirect(url_for("subscription_detail", sid=sid))


@app.post("/permissions/<int:pid>/toggle")
@write_required
def permission_toggle(pid):
    attempt("UPDATE PERMISSION SET allowed = NOT allowed WHERE permission_id=%s", (pid,), "Permission toggled.")
    return redirect(request.referrer or url_for("subscriptions"))


@app.post("/permissions/<int:pid>/delete")
@write_required
def permission_delete(pid):
    attempt("DELETE FROM PERMISSION WHERE permission_id=%s", (pid,), "Permission deleted.")
    return redirect(request.referrer or url_for("subscriptions"))


# ------------------------------------------------------------------ users (admin)
@app.route("/users")
@admin_required
def users():
    rows = db.query("SELECT U.user_id, U.full_name, U.email, U.phone, R.role_name, T.team_name, U.status, U.created_at, "
                    "(SELECT COUNT(*) FROM API A WHERE A.owner_id=U.user_id) AS owned_apis, "
                    "(SELECT COUNT(*) FROM SUBSCRIPTION S WHERE S.consumer_id=U.user_id) AS subscriptions "
                    "FROM `USER` U JOIN `ROLE` R ON U.role_id=R.role_id JOIN TEAM T ON U.team_id=T.team_id ORDER BY U.user_id")
    return render_template("users.html", rows=rows, roles=db.query("SELECT * FROM `ROLE`"), teams=db.query("SELECT * FROM TEAM"))


@app.post("/users/add")
@admin_required
def user_add():
    pw = val("password") or ""
    if len(pw) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("users"))
    attempt("INSERT INTO `USER` (full_name, email, phone, password_hash, role_id, team_id) VALUES (%s,%s,%s,%s,%s,%s)",
            (val("full_name"), val("email"), val("phone"), generate_password_hash(pw), val("role_id"), val("team_id")),
            "User created.")
    return redirect(url_for("users"))


@app.post("/users/<int:uid>/delete")
@admin_required
def user_delete(uid):
    if uid == session["user"]["id"]:
        flash("You cannot delete the account you are logged in with.", "error")
    else:
        attempt("DELETE FROM `USER` WHERE user_id=%s", (uid,), "User deleted.")
    return redirect(url_for("users"))


# ------------------------------------------------------------------ reports + concepts
@app.route("/reports")
@login_required
def reports():
    data = reports_data.get_reports_data()
    return render_template("reports.html", **data)


def dropdown_sources():
    return {
        "tables": [dict(value=t, label=t) for t in concepts.TABLES],
        "statuses": [dict(value=s, label=s) for s in API_STATUSES + ["UNKNOWN_STATUS"]],
        "owners": [dict(value=o["user_id"], label=f"{o['full_name']} ({o['role_name']}) - id {o['user_id']}") for o in owners()],
        "apis": [dict(value=a["api_id"], label=f"{a['api_name']} - id {a['api_id']}") for a in db.query("SELECT api_id, api_name FROM API ORDER BY api_id")],
    }


@app.route("/concepts", endpoint="concepts")
@app.route("/concepts", endpoint="concepts_page")
@login_required
def concepts_page():
    sections = concepts.section_defs()
    for sec in sections:
        for it in sec["entries"]:
            if it.get("define"):
                it["definition"] = concepts.definition(*it["define"])
    return render_template("concepts.html", sections=sections, sources=dropdown_sources())


@app.post("/api/concepts/run")
@login_required
def concepts_run():
    data = request.get_json(silent=True) or {}
    key = data.get("key", "")
    # Trigger / DDL / DML demos modify data (temporarily) - only roles that can write may run them
    if key in ("ddl", "dml", "dml_rollback", "unique_violation", "not_null_violation", "fk_cascade", "trigger_api", "trigger_sub", "trigger_sweep") and not can_write():
        return jsonify(error="Only Admin/Developer accounts can run data-changing demos."), 403
    try:
        return jsonify(steps=concepts.run(key, data.get("params")))
    except (ValueError, KeyError) as e:
        return jsonify(error=str(e)), 400
    except pymysql.MySQLError as e:
        return jsonify(error=f"MySQL error {e.args[0]}: {e.args[1]}"), 500


@app.errorhandler(pymysql.err.OperationalError)
def db_down(e):
    return render_template("error.html", message=f"Cannot reach MariaDB: {e.args[1] if len(e.args) > 1 else e}. "
                           "Start MySQL in XAMPP and run python setup_db.py."), 503


if __name__ == "__main__":
    app.run(debug=True, port=5000)
