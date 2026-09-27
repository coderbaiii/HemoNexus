"""
HEMONEXAS Database Utilities
Provides robust SQLite connection handling, parameter queries,
and schema initialization.
"""
import sqlite3
from pathlib import Path
from flask import g, current_app
from config import Config

def dict_factory(cursor, row):
    """Convert SQLite row to standard Python dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db(db_path=None):
    """
    Returns an active SQLite connection.
    Uses Flask 'g' context if inside an application context,
    otherwise creates a standalone connection.
    """
    if db_path is None:
        try:
            db_path = current_app.config.get("DATABASE_PATH", Config.DATABASE_PATH)
        except RuntimeError:
            db_path = Config.DATABASE_PATH

    # Inside Flask application context
    try:
        if "db" not in g:
            conn = sqlite3.connect(db_path)
            conn.row_factory = dict_factory
            conn.execute("PRAGMA foreign_keys = ON")
            g.db = conn
        return g.db
    except RuntimeError:
        # Outside Flask application context
        conn = sqlite3.connect(db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

def close_db(e=None):
    """Closes the current database connection stored on Flask context 'g'."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, db=None):
    """
    Executes a SELECT statement with parameterized arguments.
    Returns a single dictionary if one=True, or a list of dictionaries.
    """
    conn = db or get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows

def execute_db(query, args=(), db=None):
    """
    Executes an INSERT, UPDATE, or DELETE statement with parameterized arguments.
    Returns a tuple of (lastrowid, rowcount).
    """
    conn = db or get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    row_count = cur.rowcount
    cur.close()
    return last_id, row_count

def init_db(db_path=None, seed=True):
    """Initializes the database schema from schema.sql and seeds synthetic data."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_db(db_path)
    cur = conn.cursor()
    cur.executescript(schema_sql)
    conn.commit()

    if seed:
        from database.seed import seed_database
        seed_database(conn)

    cur.close()
    if db_path and db_path != ":memory:":
        conn.close()
