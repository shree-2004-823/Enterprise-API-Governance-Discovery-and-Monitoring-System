"""One-command database setup for XAMPP / MariaDB.

    python setup_db.py            # create + seed (refuses if the schema already has tables)
    python setup_db.py --reset    # DROP the api_management database first, then recreate
    python setup_db.py --hashes-only   # you imported the .sql in phpMyAdmin: just fix the password hashes

It executes sql/api_management_refined.sql UNCHANGED (tables, sample data, views,
triggers, functions, procedures). PyMySQL cannot read `DELIMITER` lines, so this script
splits the file itself (comment/quote aware). The demonstration SELECT/CALL lines at the
end of the file are skipped because they only print results.

Finally it replaces the placeholder password hashes in USER with real hashes of the
demo password (see config.DEMO_PASSWORD) so that the Flask login works.
"""
import os
import sys

import pymysql
from werkzeug.security import generate_password_hash

from config import DB, DEMO_PASSWORD

SQL_FILE = os.path.join(os.path.dirname(__file__), "sql", "api_management_refined.sql")


def split_statements(sql):
    stmts, cur, i, n, delim, line_start = [], [], 0, len(sql), ";", True
    while i < n:
        if line_start and sql[i:i + 10].upper() == "DELIMITER ":
            j = sql.find("\n", i)
            j = n if j == -1 else j
            delim = sql[i + 10:j].strip()
            i = j + 1
            continue
        c = sql[i]
        if sql.startswith("/*", i):                      # block comment
            j = sql.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if sql.startswith("--", i) or c == "#":          # line comment
            j = sql.find("\n", i)
            i = n if j == -1 else j
            continue
        if c in "'\"`":                                   # quoted string / identifier
            j = i + 1
            while j < n:
                if sql[j] == "\\" and c != "`":
                    j += 2
                    continue
                if sql[j] == c:
                    if j + 1 < n and sql[j + 1] == c:
                        j += 2
                        continue
                    break
                j += 1
            cur.append(sql[i:j + 1])
            i, line_start = j + 1, False
            continue
        if sql.startswith(delim, i):
            s = "".join(cur).strip()
            if s:
                stmts.append(s)
            cur, i = [], i + len(delim)
            continue
        cur.append(c)
        line_start = c == "\n" or (line_start and c in " \t")
        i += 1
    s = "".join(cur).strip()
    if s:
        stmts.append(s)
    return stmts


def set_hashes(cur):
    cur.execute("SELECT user_id FROM `USER` WHERE password_hash LIKE 'REPLACE_WITH_VALID%%'")
    rows = cur.fetchall()
    for (uid,) in rows:
        cur.execute("UPDATE `USER` SET password_hash=%s WHERE user_id=%s", (generate_password_hash(DEMO_PASSWORD), uid))
    print(f"Real password hashes set for {len(rows)} user(s)")


def main():
    reset = "--reset" in sys.argv
    cfg = dict(DB)
    dbname = cfg.pop("database")
    try:
        conn = pymysql.connect(**cfg, charset="utf8mb4", autocommit=True)
    except pymysql.MySQLError as e:
        sys.exit(f"Cannot connect to MySQL/MariaDB ({e}).\n"
                 f"Ensure your MySQL service or XAMPP is running, and verify host/port/user/password in .env.")
    cur = conn.cursor()
    cur.execute("SELECT VERSION()")
    print("Connected to Database:", cur.fetchone()[0])
    try:
        cur.execute("SET GLOBAL log_bin_trust_function_creators = 1")
    except Exception:
        pass
    if "--hashes-only" in sys.argv:
        cur.execute(f"USE `{dbname}`")
        set_hashes(cur)
        return
    cur.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s", (dbname,))
    if cur.fetchone()[0] and not reset:
        sys.exit(f"Database `{dbname}` already has tables. Re-run with --reset to drop and rebuild it.")
    if reset:
        cur.execute(f"DROP DATABASE IF EXISTS `{dbname}`")
        print("Dropped old database")

    with open(SQL_FILE, encoding="utf8") as f:
        statements = split_statements(f.read())
    ran = skipped = 0
    for s in statements:
        if s.split(None, 1)[0].upper() in ("SELECT", "CALL"):   # demo output queries
            skipped += 1
            continue
        cur.execute(s)
        ran += 1
    print(f"Executed {ran} statements ({skipped} demo SELECT/CALL lines skipped)")

    cur.execute(f"USE `{dbname}`")
    set_hashes(cur)

    cur.execute("SELECT (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE'),"
                "(SELECT COUNT(*) FROM information_schema.VIEWS WHERE TABLE_SCHEMA=%s),"
                "(SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=%s),"
                "(SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=%s AND ROUTINE_TYPE='FUNCTION'),"
                "(SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=%s AND ROUTINE_TYPE='PROCEDURE')",
                (dbname,) * 5)
    t, v, tr, fn, pr = cur.fetchone()
    print(f"Created: {t} tables, {v} views, {tr} triggers, {fn} functions, {pr} procedures")
    print("Done. Now run:  python app.py")


if __name__ == "__main__":
    main()
