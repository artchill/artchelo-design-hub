"""Migration for the Attendance Ticket workflow.

- Creates the attendance_tickets table if it doesn't exist

Idempotent — safe to run multiple times. Existing tables/data are untouched.
Usage: python migrate_attendance_tickets.py
"""
import sqlite3
from pathlib import Path

from app import app
from models import db

DB_PATH = Path(app.instance_path) / 'attendance.db'


def table_exists(name):
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None
    finally:
        conn.close()


def migrate():
    if not DB_PATH.exists():
        print(f'Database not found at {DB_PATH} — nothing to migrate.')
        return

    had_table = table_exists('attendance_tickets')
    # create_all only creates missing tables; existing tables/data are untouched
    with app.app_context():
        db.create_all()
    print('attendance_tickets table already present.' if had_table
          else 'Created attendance_tickets table.')
    print('Migration complete.')


if __name__ == '__main__':
    migrate()
