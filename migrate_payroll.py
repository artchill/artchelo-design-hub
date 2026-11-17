"""Payroll schema migration (fixed-salary model). Idempotent — safe to re-run; touches no payroll data.

  - attendances.ot_hours_regular / ot_hours_restday / actual_hours (kept dormant for the P-2 OT module)
  - users.daily_hours (default 8; part-timers backfilled to 4 when the column is first added)
  - payroll_run / payroll_entry tables; payroll_entry columns brought in line with the model
    (adds the fixed-salary columns, drops the hourly-model ones only when the table is empty)

Run:  python migrate_payroll.py      (rebuild_payroll.py also calls migrate())
"""
from app import app, db
from models import PayrollRun, PayrollEntry  # noqa: F401  (registers tables for create_all)
from sqlalchemy import text, inspect

PAYROLL_ENTRY_NEW_COLUMNS = {
    'monthly_salary': 'FLOAT DEFAULT 0',
    'daily_hours': 'FLOAT DEFAULT 8.0',
    'daily_rate': 'FLOAT DEFAULT 0',
    'hourly_rate': 'FLOAT DEFAULT 0',
    'base_pay': 'FLOAT DEFAULT 0',
    'expected_workdays': 'INTEGER DEFAULT 0',
    'absent_days': 'FLOAT DEFAULT 0',
    'absent_deduction': 'FLOAT DEFAULT 0',
    'late_minutes': 'FLOAT DEFAULT 0',
    'late_deduction': 'FLOAT DEFAULT 0',
    'undertime_hours': 'FLOAT DEFAULT 0',
    'undertime_deduction': 'FLOAT DEFAULT 0',
}
# From the superseded hourly model (basic_pay -> base_pay, late_undertime -> late/undertime split)
PAYROLL_ENTRY_STALE_COLUMNS = ('basic_pay', 'hours_worked', 'late_undertime')


def columns(table):
    return [c['name'] for c in inspect(db.engine).get_columns(table)]


def add_column(conn, table, existing, name, ddl):
    if name in existing:
        return False
    print(f'  Adding {table}.{name}...')
    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
    return True


def migrate():
    print('---------- schema ----------')
    tables = inspect(db.engine).get_table_names()
    with db.engine.begin() as conn:
        att_cols = columns('attendances')
        add_column(conn, 'attendances', att_cols, 'ot_hours_regular', 'FLOAT DEFAULT 0')
        add_column(conn, 'attendances', att_cols, 'ot_hours_restday', 'FLOAT DEFAULT 0')
        add_column(conn, 'attendances', att_cols, 'actual_hours', 'FLOAT')

        if add_column(conn, 'users', columns('users'), 'daily_hours', 'FLOAT DEFAULT 8.0'):
            n = conn.execute(text("UPDATE users SET daily_hours = 4.0 WHERE employee_type = 'part-time'")).rowcount
            print(f'  Backfilled daily_hours: {n} part-time user(s) = 4 h, everyone else = 8 h.')
        else:
            print('  users.daily_hours already exists.')

        if 'payroll_entry' in tables:
            pe_cols = columns('payroll_entry')
            added = [c for c, ddl in PAYROLL_ENTRY_NEW_COLUMNS.items() if add_column(conn, 'payroll_entry', pe_cols, c, ddl)]
            if not added:
                print('  payroll_entry fixed-salary columns already exist.')
            stale = [c for c in PAYROLL_ENTRY_STALE_COLUMNS if c in pe_cols]
            if stale:
                rows = conn.execute(text('SELECT COUNT(*) FROM payroll_entry')).scalar()
                if rows == 0:
                    for c in stale:
                        print(f'  Dropping unused payroll_entry.{c}...')
                        conn.execute(text(f'ALTER TABLE payroll_entry DROP COLUMN {c}'))
                else:
                    print(f'  Keeping unused payroll_entry columns {stale} ({rows} rows exist).')

    db.create_all()  # payroll_run / payroll_entry on a fresh database
    print('  payroll_run / payroll_entry tables OK.')


if __name__ == '__main__':
    with app.app_context():
        migrate()
