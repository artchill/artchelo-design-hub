"""One-off: rebuild payroll on the FIXED MONTHLY SALARY model.

DESTRUCTIVE: deletes every PayrollRun and PayrollEntry (fresh start), then
  - brings the schema in line (migrate_payroll.migrate(): users.daily_hours, payroll_entry columns)
  - reverts Chilli's salary from the FTE value (35,000) to actual pay (17,500)

Run once:  python rebuild_payroll.py
"""
from app import app, db
from models import PayrollRun, PayrollEntry, User, PAYROLL_WORKDAYS_PER_MONTH
from migrate_payroll import migrate

# Chilli's employee account. NOTE: 'cheluarbuis' is the super-admin and is never a payroll
# subject; Chilli (Richellou, part-time, 2-6 PM) is cheloart92.
CHILLI_USERNAME = 'cheloart92'

with app.app_context():
    print('========== PAYROLL REBUILD ==========')
    print()

    # Schema first: the User model now has daily_hours, so it must exist before any User query
    migrate()
    print()

    # 1. Delete all existing payroll data (fresh start)
    count_entries = PayrollEntry.query.count()
    count_runs = PayrollRun.query.count()
    print(f'Deleting {count_entries} payroll entries...')
    PayrollEntry.query.delete()
    print(f'Deleting {count_runs} payroll runs...')
    PayrollRun.query.delete()
    db.session.commit()
    print('Existing payroll data cleared.')
    # Again now that payroll_entry is empty, so the hourly-model columns can be dropped
    migrate()
    print()

    # 2. Revert Chilli's salary from FTE back to actual
    chilli = User.query.filter_by(username=CHILLI_USERNAME).first()
    if chilli:
        current_salary = chilli.monthly_salary
        print(f'Chilli ({CHILLI_USERNAME}) current salary: ₱{(current_salary or 0):,.2f}')
        if current_salary == 35000:
            chilli.monthly_salary = 17500
            print('Reverted to actual: ₱17,500')
        elif current_salary == 17500:
            print('Already correct: ₱17,500 (actual part-time pay)')
        else:
            print('Unknown value — leaving as is. Update manually if needed.')
        db.session.commit()

    print()
    print('========== VERIFICATION ==========')
    # admin + employee only — super-admin salaries are never printed
    users = User.query.filter(User.role.in_(['admin', 'employee']),
                              User.employment_status == 'active').order_by(User.id).all()
    for u in users:
        hourly = (u.monthly_salary / PAYROLL_WORKDAYS_PER_MONTH / (u.daily_hours or 8)) if u.monthly_salary else 0
        base = (u.monthly_salary / 2) if u.monthly_salary else 0
        print(f'  {u.username} ({u.employee_type}): salary=₱{(u.monthly_salary or 0):,.2f}, '
              f'daily_hours={u.daily_hours}, hourly=₱{hourly:.2f}, semi-mo base=₱{base:,.2f}')

    print()
    chilli_check = User.query.filter_by(username=CHILLI_USERNAME).first()
    if chilli_check:
        expected_base = (chilli_check.monthly_salary or 0) / 2
        print(f'Chilli Oct 1-15 base pay (if no deductions): ₱{expected_base:,.2f}')
        if abs(expected_base - 8750) < 1 and chilli_check.daily_hours == 4:
            print('✅ MATCHES VOUCHER ₱8,750')
        else:
            print('⚠️ Expected ₱8,750 — check Chilli salary = ₱17,500 and daily_hours = 4')

    print()
    print('========== REBUILD COMPLETE ==========')
