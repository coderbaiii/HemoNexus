import sqlite3
from flask import g, current_app
from backend.config import Config

def get_db(db_path=None):
    """
    Get a database connection. If running inside a Flask app context,
    reuse the connection stored on flask.g. Otherwise, return a new connection.
    Foreign key enforcement is enabled on all connections.
    """
    # Check if inside Flask request/app context
    try:
        from flask import has_app_context
        if has_app_context():
            if "_database" not in g:
                path = db_path or current_app.config.get("DATABASE_PATH", Config.DATABASE_PATH)
                conn = sqlite3.connect(path, timeout=10.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                g._database = conn
            return g._database
    except (ImportError, RuntimeError):
        pass

    # Standalone connection
    path = db_path or Config.DATABASE_PATH
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def close_db(e=None):
    """Close the database connection at the end of the request."""
    try:
        db = g.pop("_database", None)
        if db is not None:
            db.close()
    except Exception:
        pass

def dict_from_row(row):
    """Convert a sqlite3.Row to a standard python dict."""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}

def query_db(query, args=(), one=False, db=None):
    """
    Execute a parameterized SQL SELECT query and return rows as dictionaries.
    """
    conn = db or get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    rows = cur.fetchall()
    cur.close()
    
    if one:
        return dict_from_row(rows[0]) if rows else None
    return [dict_from_row(r) for r in rows]

def execute_db(query, args=(), commit=True, db=None):
    """
    Execute a parameterized SQL INSERT, UPDATE, or DELETE statement.
    Returns (lastrowid, rowcount).
    """
    conn = db or get_db()
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
    last_id = cur.lastrowid
    row_count = cur.rowcount
    cur.close()
    return last_id, row_count
