"""
Bridge module for backend.init_db delegating to database/db.py and database/seed.py.
"""
from database.db import init_db
from database.seed import seed_database

def init_database(db_path=None, seed_demo=True):
    init_db(db_path=db_path, seed=seed_demo)

if __name__ == "__main__":
    init_database()
