"""Payroll migration (Phase P-1, universal 176-hour formula). Idempotent — safe to re-run.

  - attendances.ot_hours_regular / ot_hours_restday / actual_hours
  - payroll_run / payroll_entry tables (+ hourly snapshot columns on older payroll_entry tables)
  - removes the daily_hours columns from the earlier per-employee-hours draft (no longer used)

Formula: hourly_rate = monthly_salary (full-time equivalent) / 176.
Run:  python migrate_payroll.py
"""
from app import app, db
from models import User, PayrollRun, PayrollEntry, STANDARD_MONTHLY_HOURS  # noqa: F401
from sqlalchemy import text, inspect

# The voucher account. NOTE: 'cheluarbuis' is the super-admin and is never a payroll subject;
# Chilli's employee account (Richellou, part-time, 2-6 PM attendance) is cheloart92.
CHILLI_USERNAME = 'cheloart92'


def columns(table):
    return [c['name'] for c in inspect(db.engine).get_columns(table)]


def add_column(conn, table, existing, name, ddl):
    if name in existing:
        print(f'  {table}.{name} already exists.')
        return
    print(f'  Adding {table}.{name}...')
    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))


with app.app_context():
    print('========== PAYROLL MIGRATION ==========')
    tables = inspect(db.engine).get_table_names()
    att_cols = columns('attendances')

    with db.engine.begin() as conn:
        add_column(conn, 'attendances', att_cols, 'ot_hours_regular', 'FLOAT DEFAULT 0')
        add_column(conn, 'attendances', att_cols, 'ot_hours_restday', 'FLOAT DEFAULT 0')
        add_column(conn, 'attendances', att_cols, 'actual_hours', 'FLOAT')

        if 'payroll_entry' in tables:
            pe_cols = columns('payroll_entry')
            for name, ddl in (('monthly_salary', 'FLOAT DEFAULT 0'), ('hourly_rate', 'FLOAT DEFAULT 0'),
                              ('hours_worked', 'FLOAT DEFAULT 0')):
                add_column(conn, 'payroll_entry', pe_cols, name, ddl)

        # daily_hours (users + payroll_entry) came from the superseded per-employee-hours version
        for table in ('users', 'payroll_entry'):
            if table in tables and 'daily_hours' in columns(table):
                print(f'  Dropping unused {table}.daily_hours...')
                conn.execute(text(f'ALTER TABLE {table} DROP COLUMN daily_hours'))

    print('Creating payroll_run and payroll_entry tables (if not exist)...')
    db.create_all()

    # Entries from the original daily-rate version (if any never got an hourly snapshot):
    # a full day = 8 h, so hourly_rate x hours_worked reproduces the stored basic pay.
    if 'daily_rate' in columns('payroll_entry'):
        with db.engine.begin() as conn:
            n = conn.execute(text('''
                UPDATE payroll_entry SET
                    monthly_salary = ROUND(daily_rate * 22, 2),
                    hourly_rate    = ROUND(daily_rate / 8, 2),
                    hours_worked   = days_worked * 8
                WHERE COALESCE(hourly_rate, 0) = 0 AND COALESCE(daily_rate, 0) > 0''')).rowcount
            if n:
                print(f'  Backfilled hourly snapshot on {n} legacy payroll entr{"y" if n == 1 else "ies"} '
                      f'(pay amounts unchanged).')

    print()
    print('========== VERIFICATION ==========')
    # admin + employee only — super-admin salaries are never printed
    users = User.query.filter(User.role.in_(['admin', 'employee']),
                              User.employment_status == 'active').order_by(User.id).all()
    for u in users:
        hourly = (u.monthly_salary / STANDARD_MONTHLY_HOURS) if u.monthly_salary else 0
        print(f'  {u.username} ({u.employee_type}): FTE salary=₱{(u.monthly_salary or 0):,.2f}, hourly=₱{hourly:.2f}')

    print()
    chilli = User.query.filter_by(username=CHILLI_USERNAME).first()
    if chilli:
        print(f'Chilli voucher verification ({CHILLI_USERNAME}, Oct 1-15, 2026 target: ₱8,750):')
        hourly = (chilli.monthly_salary / STANDARD_MONTHLY_HOURS) if chilli.monthly_salary else 0
        print('  Expected hourly (if FTE=₱35,000): ₱198.86')
        print(f'  Current stored monthly_salary: ₱{(chilli.monthly_salary or 0):,.2f}')
        print(f'  Computed hourly: ₱{hourly:.2f}')
        print(f'  Employee type: {chilli.employee_type}')
        if abs(hourly - 198.86) < 0.5:
            print('  ✅ FTE salary is correct — payroll will compute ₱8,750 for Chilli')
        else:
            print("  ⚠️ ACTION NEEDED: Chilli's monthly_salary should be ₱35,000 (full-time equivalent)")
            print('  Currently stored as actual part-time pay. Update via:')
            print('  Admin > Team > Edit Chilli > monthly_salary = 35000')
            print('  This stores the "full rate" so the system can pay proportionally.')

    print()
    print('========== MIGRATION COMPLETE ==========')
