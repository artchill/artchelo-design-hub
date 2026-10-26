"""One-time migration: promote cheluarbuis to super-admin.

Safe to run multiple times — does nothing if the user is already super-admin.
Usage: python migrate_super_admin.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'instance' / 'attendance.db'
USERNAME = 'cheluarbuis'
NEW_ROLE = 'super-admin'


def migrate():
    if not DB_PATH.exists():
        print(f'Database not found at {DB_PATH} — nothing to migrate.')
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            'SELECT id, role FROM users WHERE username = ?', (USERNAME,)
        ).fetchone()
        if row is None:
            print(f'User "{USERNAME}" not found — nothing changed.')
            return

        user_id, old_role = row
        if old_role == NEW_ROLE:
            print(f'User "{USERNAME}" (id={user_id}) is already {NEW_ROLE} — nothing changed.')
            return

        conn.execute(
            'UPDATE users SET role = ? WHERE username = ?', (NEW_ROLE, USERNAME)
        )
        conn.commit()
        print(f'Updated "{USERNAME}" (id={user_id}): role {old_role!r} -> {NEW_ROLE!r}')
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
