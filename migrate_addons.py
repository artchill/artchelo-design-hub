"""Create the add_ons table. Idempotent: db.create_all() only creates missing tables.

Run once:  python migrate_addons.py
"""
from app import app, db
import models  # noqa: F401  (registers AddOn on the metadata)

with app.app_context():
    db.create_all()
    print("add_ons table ensured.")
    print("Migration complete.")
