"""One-off: re-apply PayrollEntry.recalculate() (proportional absent deduction) to every DRAFT run.
Finalized and paid runs are left untouched. Safe to re-run.  Run:  python fix_payroll_entries.py
"""
from app import app, db, refresh_payroll_totals
from models import PayrollRun

with app.app_context():
    print('Recalculating all DRAFT payroll entries with fixed formula...')
    draft_runs = PayrollRun.query.filter_by(status='draft').all()
    for run in draft_runs:
        for entry in run.entries:
            entry.recalculate()
        refresh_payroll_totals(run)  # same totals logic the app uses (skips super-admin rows)
        print(f'  {run.title}: Gross=₱{run.total_gross:,.2f}, Deductions=₱{run.total_deductions:,.2f}, '
              f'Net=₱{run.total_net:,.2f}')
    if not draft_runs:
        print('  No draft payroll runs.')
    db.session.commit()
    print('Done.')
