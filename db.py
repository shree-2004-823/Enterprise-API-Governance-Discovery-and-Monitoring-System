"""Thin MariaDB access layer (PyMySQL). No business logic lives here."""
import datetime
import decimal

import pymysql
import pymysql.cursors
from flask import g

from config import DB


def connect(with_database=True, dict_rows=True):
    cfg = dict(DB)
    if not with_database:
        cfg.pop("database")
    return pymysql.connect(
        **cfg,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor if dict_rows else pymysql.cursors.Cursor,
    )


def clean(v):
    """Make a MariaDB value JSON/template friendly."""
    if isinstance(v, decimal.Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, datetime.datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, (datetime.date, datetime.timedelta)):
        return str(v)
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf8", "replace")
    return v


def clean_rows(rows):
    return [[clean(c) for c in r] if not isinstance(r, dict) else {k: clean(c) for k, c in r.items()} for r in rows]


def conn():
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_exc=None):
    c = g.pop("db", None)
    if c is not None:
        c.close()


def query(sql, args=None, one=False):
    with conn().cursor() as cur:
        cur.execute(sql, args)
        rows = clean_rows(cur.fetchall())
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=None):
    """Run INSERT/UPDATE/DELETE. Returns (affected_rows, last_insert_id)."""
    with conn().cursor() as cur:
        cur.execute(sql, args)
        return cur.rowcount, cur.lastrowid


def call_proc(name, args=()):
    """CALL a stored procedure and return EVERY result set it produced.

    PyMySQL exposes the first result set after execute(); additional result sets
    (and the trailing OK packet every CALL sends) must be consumed with nextset(),
    otherwise the connection raises 'Commands out of sync'.
    """
    allowed = {"get_apis_by_owner": 1, "get_api_subscriptions": 1}
    if name not in allowed or len(args) != allowed[name]:
        raise ValueError("procedure not allowed")
    marks = ", ".join(["%s"] * len(args))
    sets = []
    with conn().cursor(pymysql.cursors.Cursor) as cur:
        cur.execute(f"CALL {name}({marks})", args)
        while True:
            if cur.description:
                sets.append({"columns": [d[0] for d in cur.description],
                             "rows": clean_rows(cur.fetchall())})
            if not cur.nextset():
                break
    return sets
