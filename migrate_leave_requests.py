"""Migration for Phase L-3 (leave request workflow).

- Creates the leave_requests table if it doesn't exist
- Adds leave_days.request_id (nullable FK -> leave_requests.id) if missing

Idempotent — safe to run multiple times.
Usage: python migrate_leave_requests.py
"""
import sqlite3
from pathlib import Path

from app import app
from models import db

DB_PATH = Path(app.instance_path) / 'attendance.db'


def table_exists(conn, name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def migrate():
    if not DB_PATH.exists():
        print(f'Database not found at {DB_PATH} — nothing to migrate.')
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        had_table = table_exists(conn, 'leave_requests')
    finally:
        conn.close()

    # create_all only creates missing tables; existing tables/data are untouched
    with app.app_context():
        db.create_all()
    print('leave_requests table already present.' if had_table else 'Created leave_requests table.')

    conn = sqlite3.connect(DB_PATH)
    try:
        cols = [row[1] for row in conn.execute('PRAGMA table_info(leave_days)')]
        if 'request_id' in cols:
            print('leave_days.request_id already present.')
        else:
            conn.execute(
                'ALTER TABLE leave_days ADD COLUMN request_id INTEGER REFERENCES leave_requests(id)'
            )
            conn.commit()
            print('Added request_id column to leave_days.')
    finally:
        conn.close()

    print('Migration complete.')


if __name__ == '__main__':
    migrate()
