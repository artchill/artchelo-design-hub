"""One-off data fix: backfill Oct 1 - Nov 16, 2026 attendance for @cheloart92.

Run once:  python backfill_cheloart_attendance.py
Re-running is safe: days that already have attendance are skipped.
"""
from app import app, db
from models import User, Attendance
from datetime import datetime, date, time, timedelta

TARGET_USERNAME = 'cheloart92'
BACKFILLER_USERNAME = 'cheluarbuis'

REGULAR_TASK = 'Working on Akari, AFSI, HUB & CRM websites'

# Only WEEKDAY holidays get special task labels. Weekend holidays are skipped entirely.
HOLIDAYS = {
    date(2026, 11, 1): 'All Saints\' Day',  # Sunday — listed so the summary reports it as skipped
    date(2026, 11, 2): 'All Souls\' Day - Working on CRM',
}

START_DATE = date(2026, 10, 1)
END_DATE = date(2026, 11, 16)

TIME_IN = time(14, 0)
TIME_OUT = time(18, 0)

with app.app_context():
    target_user = User.query.filter_by(username=TARGET_USERNAME).first()
    if not target_user:
        print(f'ERROR: user {TARGET_USERNAME} not found. Available users:')
        for u in User.query.all():
            print(f'  - {u.username} ({u.full_name})')
        exit(1)

    backfiller = User.query.filter_by(username=BACKFILLER_USERNAME).first()
    if not backfiller:
        print(f'ERROR: backfiller {BACKFILLER_USERNAME} not found')
        exit(1)

    created_count = 0
    skipped_existing = 0
    skipped_weekend = 0
    weekend_holidays_skipped = []

    current = START_DATE
    while current <= END_DATE:
        weekday = current.weekday()  # 0=Mon, 6=Sun
        is_weekend = weekday >= 5

        if is_weekend:
            # Weekend — skip regardless of holiday status
            if current in HOLIDAYS:
                weekend_holidays_skipped.append(current)
            skipped_weekend += 1
            current += timedelta(days=1)
            continue

        # Check for existing attendance
        day_start = datetime.combine(current, datetime.min.time())
        day_end = datetime.combine(current, datetime.max.time())
        existing = Attendance.query.filter(
            Attendance.user_id == target_user.id,
            Attendance.datetime_in >= day_start,
            Attendance.datetime_in <= day_end,
        ).first()

        if existing:
            skipped_existing += 1
            current += timedelta(days=1)
            continue

        # Determine task
        if current in HOLIDAYS:
            task_note = HOLIDAYS[current]
        else:
            task_note = REGULAR_TASK

        datetime_in = datetime.combine(current, TIME_IN)
        datetime_out = datetime.combine(current, TIME_OUT)
        total_hours = round((datetime_out - datetime_in).total_seconds() / 3600, 2)

        new_rec = Attendance(
            user_id=target_user.id,
            datetime_in=datetime_in,
            datetime_out=datetime_out,
            day=current.strftime('%A'),
            task_report=task_note,
            total_hours=total_hours,
            edited_at=datetime.now(),
            edited_by_id=backfiller.id,
        )
        db.session.add(new_rec)
        created_count += 1
        print(f'  Created: {current.strftime("%Y-%m-%d %A")} — {task_note[:60]}')

        current += timedelta(days=1)

    db.session.commit()

    print()
    print('========== BACKFILL COMPLETE ==========')
    print(f'Target user: {target_user.full_name} (@{target_user.username})')
    print(f'Date range: {START_DATE} to {END_DATE}')
    print(f'Created: {created_count} attendance records')
    print(f'Skipped (already existed): {skipped_existing}')
    print(f'Skipped (weekends): {skipped_weekend}')
    if weekend_holidays_skipped:
        print(f'Weekend holidays skipped: {", ".join(d.strftime("%b %d") for d in weekend_holidays_skipped)}')
    print(f'Backfilled by: {backfiller.full_name}')
    print()
    print('Next step: open the attendance tracker for @cheloart92 and verify October + November.')
