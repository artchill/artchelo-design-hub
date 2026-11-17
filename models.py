from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date

db = SQLAlchemy()

# Payroll: fixed monthly salary; daily rate = salary / 22
PAYROLL_WORKDAYS_PER_MONTH = 22
# Attendance hour rules (used by Attendance.compute_hours_worked; not part of payroll since the
# fixed-salary rebuild — kept for the P-2 OT Request module)
STANDARD_DAILY_HOURS = 8
LUNCH_BREAK_THRESHOLD = 6  # a day longer than this has 1 h unpaid lunch deducted


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fname = db.Column(db.String(80), nullable=False)
    mname = db.Column(db.String(5), nullable=True)  # middle initial (e.g. "L" or "L.")
    lname = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    codename = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_pic = db.Column(db.String(255), nullable=True)  # filename in static/uploads/avatars/
    gender = db.Column(db.String(20), nullable=True)  # male/female/prefer_not_to_say
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Profile fields
    job_position = db.Column(db.String(100), nullable=True)
    birthdate = db.Column(db.Date, nullable=True)
    date_hired = db.Column(db.Date, nullable=True)
    monthly_salary = db.Column(db.Float, nullable=True)
    employee_type = db.Column(db.String(20), nullable=True)
    employment_status = db.Column(db.String(20), default='active')
    daily_hours = db.Column(db.Float, default=8.0)  # 8 full-time, 4 part-time; derives the hourly rate
    resignation_date = db.Column(db.Date, nullable=True)

    attendances = db.relationship(
        'Attendance', foreign_keys='Attendance.user_id',
        backref='user', lazy=True,
    )
    leave_days = db.relationship(
        'LeaveDay', foreign_keys='LeaveDay.user_id',
        backref='user', lazy=True,
    )

    @property
    def age(self):
        if not self.birthdate:
            return None
        today = date.today()
        return today.year - self.birthdate.year - (
            (today.month, today.day) < (self.birthdate.month, self.birthdate.day)
        )

    @property
    def is_active_employee(self):
        return self.employment_status == 'active'

    @property
    def is_leave_eligible(self):
        """Only full-time employees are eligible for VL/SL leaves."""
        return self.employee_type == 'full-time'

    @property
    def hourly_rate(self):
        """(monthly_salary / 22) / daily_hours. monthly_salary is ACTUAL pay."""
        if not self.monthly_salary or not self.daily_hours:
            return 0
        daily = self.monthly_salary / PAYROLL_WORKDAYS_PER_MONTH
        return round(daily / self.daily_hours, 2)

    @property
    def is_super_admin(self):
        return self.role == 'super-admin'

    @property
    def is_admin_or_above(self):
        return self.role in ('admin', 'super-admin')

    @property
    def full_name(self):
        """Returns 'First M. Last' if middle initial exists, else 'First Last'."""
        mi = (self.mname or '').strip().rstrip('.')
        if mi:
            return f"{self.fname} {mi}. {self.lname}"
        return f"{self.fname} {self.lname}"

    @property
    def initials(self):
        """Two-letter initials for avatar badges."""
        return (self.fname[0] + self.lname[0]).upper()

    @property
    def avatar_url(self):
        """URL of the uploaded profile picture, or None to fall back to initials."""
        if not self.profile_pic:
            return None
        return url_for('static', filename='uploads/avatars/' + self.profile_pic)


class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    datetime_in = db.Column(db.DateTime, nullable=False)
    datetime_out = db.Column(db.DateTime, nullable=True)
    day = db.Column(db.String(20), nullable=False)
    total_hours = db.Column(db.Float, nullable=True)
    task_report = db.Column(db.Text, nullable=True)
    edited_at = db.Column(db.DateTime, nullable=True)
    edited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ot_hours_regular = db.Column(db.Float, default=0.0)  # OT on regular weekdays (1.25x)
    ot_hours_restday = db.Column(db.Float, default=0.0)  # OT on rest days/holidays (1.69x)
    actual_hours = db.Column(db.Float, nullable=True)     # payroll override of computed hours

    edited_by = db.relationship('User', foreign_keys=[edited_by_id])

    def compute_hours_worked(self):
        """Regular (non-OT) hours to pay for this day.

        actual_hours override wins. Otherwise time_out - time_in, minus a 1 h lunch break when
        the span is over 6 h, capped at 8 h — time beyond 8 h is overtime and is paid only via
        the OT fields (otherwise it would be paid twice). No time-out -> 8 h fallback.
        """
        if self.actual_hours is not None:
            return self.actual_hours
        if self.datetime_in and self.datetime_out:
            hours = (self.datetime_out - self.datetime_in).total_seconds() / 3600
            if hours > LUNCH_BREAK_THRESHOLD:
                hours -= 1
            return round(min(hours, float(STANDARD_DAILY_HOURS)), 2)
        return float(STANDARD_DAILY_HOURS)

    def edit_visible_to(self, viewer):
        """Whether `viewer` may see that this record was edited.
        Super-admin edits (and edits with no recorded editor) are shown only to super-admins."""
        if not self.edited_at:
            return False
        if viewer.is_super_admin:
            return True
        return self.edited_by is not None and not self.edited_by.is_super_admin


class LeaveDay(db.Model):
    __tablename__ = 'leave_days'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(10), nullable=False)
    note = db.Column(db.Text, nullable=True)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Set when the day was created by approving a LeaveRequest; NULL for direct admin marks
    request_id = db.Column(db.Integer, db.ForeignKey('leave_requests.id'), nullable=True)

    marked_by = db.relationship('User', foreign_keys=[marked_by_id])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date_leave'),
    )


class LeaveRequest(db.Model):
    """An employee's VL/SL request awaiting (or past) admin approval."""
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(10), nullable=False)        # 'vl' or 'sl'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)                # == start_date for single-day
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending/approved/rejected/cancelled
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # approver OR rejecter
    approved_at = db.Column(db.DateTime, nullable=True)          # decision time (approve or reject)
    admin_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    user = db.relationship('User', foreign_keys=[user_id], backref='leave_requests')
    approver = db.relationship('User', foreign_keys=[approved_by_id])

    @property
    def day_count(self):
        """Number of calendar days this request spans (inclusive)."""
        return (self.end_date - self.start_date).days + 1

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def status_badge_class(self):
        return {
            'pending': 'bg-amber-100 text-amber-700',
            'approved': 'bg-green-100 text-green-700',
            'rejected': 'bg-red-100 text-red-700',
            'cancelled': 'bg-slate-100 text-slate-500',
            'voided': 'bg-orange-100 text-orange-700',
        }.get(self.status, 'bg-slate-100 text-slate-500')

    def details(self):
        """Payload for the View modal (showLeaveDetails in base.html)."""
        return {
            'employee': self.user.full_name,
            'type': self.leave_type.upper(),
            'dates': self.date_range_label,
            'days': str(self.day_count),
            'status': self.status,
            'reason': self.reason,
            'admin_note': self.admin_note or '',
            'approver': self.approver.full_name if self.approver else '',
            'approved_at': self.approved_at.strftime('%b %d, %Y %I:%M %p') if self.approved_at else '',
        }

    @property
    def date_range_label(self):
        if self.start_date == self.end_date:
            return self.start_date.strftime('%b %d, %Y')
        if self.start_date.year == self.end_date.year:
            return f"{self.start_date.strftime('%b %d')} – {self.end_date.strftime('%b %d, %Y')}"
        return f"{self.start_date.strftime('%b %d, %Y')} – {self.end_date.strftime('%b %d, %Y')}"


class AttendanceTicket(db.Model):
    """An employee's request to correct one day's attendance, reviewed by an admin."""
    __tablename__ = 'attendance_tickets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # 'forgot_time_in', 'forgot_time_out', 'wrong_times', 'missing_task', 'other'
    ticket_type = db.Column(db.String(30), nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    proposed_time_in = db.Column(db.Time, nullable=True)
    proposed_time_out = db.Column(db.Time, nullable=True)
    proposed_task_report = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    # 'pending', 'approved', 'rejected', 'cancelled', 'voided'
    status = db.Column(db.String(20), nullable=False, default='pending')
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    admin_note = db.Column(db.Text, nullable=True)
    applied_change_summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    user = db.relationship('User', foreign_keys=[user_id], backref='attendance_tickets')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])

    TYPE_LABELS = {
        'forgot_time_in': 'Forgot to Time In',
        'forgot_time_out': 'Forgot to Time Out',
        'wrong_times': 'Wrong Time In/Out',
        'missing_task': 'Missing Task Report',
        'other': 'Other',
    }

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.ticket_type, self.ticket_type)

    @property
    def status_badge_class(self):
        return {
            'pending': 'bg-amber-100 text-amber-700',
            'approved': 'bg-green-100 text-green-700',
            'rejected': 'bg-red-100 text-red-700',
            'cancelled': 'bg-slate-100 text-slate-500',
            'voided': 'bg-orange-100 text-orange-700',
        }.get(self.status, 'bg-slate-100 text-slate-500')

    def details(self):
        """Payload for the View modal (showTicketDetails in base.html)."""
        fmt = lambda t: t.strftime('%I:%M %p') if t else ''
        return {
            'employee': self.user.full_name,
            'type': self.type_label,
            'target_date': self.target_date.strftime('%b %d, %Y (%A)'),
            'time_in': fmt(self.proposed_time_in),
            'time_out': fmt(self.proposed_time_out),
            'task_report': self.proposed_task_report or '',
            'reason': self.reason,
            'status': self.status,
            'admin_note': self.admin_note or '',
            'applied': self.applied_change_summary or '',
            'reviewer': self.reviewer.full_name if self.reviewer else '',
            'reviewed_at': self.reviewed_at.strftime('%b %d, %Y %I:%M %p') if self.reviewed_at else '',
        }


# ========== Clients & Sales ==========

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    client_type = db.Column(db.String(20), default='author')
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leads = db.relationship('SalesLead', backref='client', lazy=True)
    invoices = db.relationship('SalesInvoice', backref='client', lazy=True)
    projects = db.relationship('Project', backref='client', lazy=True)


class SalesLead(db.Model):
    __tablename__ = 'sales_leads'
    id = db.Column(db.Integer, primary_key=True)
    prospect_name = db.Column(db.String(200), nullable=False)
    prospect_email = db.Column(db.String(200), nullable=True)
    prospect_phone = db.Column(db.String(50), nullable=True)
    source = db.Column(db.String(50), nullable=True)
    service_interest = db.Column(db.String(100), nullable=True)
    estimated_value = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='new')
    next_followup_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)


class SalesInvoice(db.Model):
    __tablename__ = 'sales_invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    paid_date = db.Column(db.Date, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='draft')
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ========== NEW: Website Projects ==========

class Project(db.Model):
    """A website build/takeover project for a client."""
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    domain = db.Column(db.String(200), nullable=True)
    service_type = db.Column(db.String(20), default='website')  # website/takeover
    package_tier = db.Column(db.String(20), nullable=True)      # Bronze/Silver/Gold/Essential/Advanced/Elite
    tier_rank = db.Column(db.Integer, nullable=True)            # 1=lowest, 3=highest
    status = db.Column(db.String(20), default='lead')           # lead/ongoing/completed/needs_review
    created_month = db.Column(db.Integer, nullable=True)        # 1-12
    created_year = db.Column(db.Integer, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    delivered_date = db.Column(db.Date, nullable=True)
    tat_days = db.Column(db.Integer, nullable=True)             # auto-computed
    drive_url = db.Column(db.String(500), nullable=True)
    form_url = db.Column(db.String(500), nullable=True)
    assigned_developer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_developer = db.relationship('User', foreign_keys=[assigned_developer_id])
    renewals = db.relationship('DomainRenewal', backref='project', lazy=True,
                               cascade='all, delete-orphan')
    status_history = db.relationship('ProjectStatusHistory', backref='project', lazy=True,
                                     cascade='all, delete-orphan')

    @property
    def display_name(self):
        """Projects have no name column: show the domain, else the client name."""
        return self.domain or (self.client.name if self.client else f'Project #{self.id}')


class AddOn(db.Model):
    """A subscription or extra sold with a project (domain, hosting, SEO, ...)."""
    __tablename__ = 'add_ons'

    CATEGORY_LABELS = {
        'domain': 'Domain',
        'hosting': 'Hosting',
        'ssl': 'SSL Certificate',
        'email': 'Email Hosting',
        'maintenance': 'Maintenance',
        'content': 'Content Package',
        'seo': 'SEO Package',
        'social': 'Social Media',
        'logo': 'Logo Design',
        'copywriting': 'Copywriting',
        'custom': 'Other',
    }
    CATEGORY_ICONS = {
        'domain': 'fa-globe',
        'hosting': 'fa-server',
        'ssl': 'fa-lock',
        'email': 'fa-envelope',
        'maintenance': 'fa-wrench',
        'content': 'fa-file-lines',
        'seo': 'fa-magnifying-glass-chart',
        'social': 'fa-hashtag',
        'logo': 'fa-palette',
        'copywriting': 'fa-pen',
        'custom': 'fa-box',
    }
    STATUS_BADGES = {
        'active': 'bg-green-100 text-green-700',
        'pending': 'bg-amber-100 text-amber-700',
        'expired': 'bg-red-100 text-red-700',
        'cancelled': 'bg-slate-100 text-slate-500',
        'renewed': 'bg-blue-100 text-blue-700',
    }

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    duration_label = db.Column(db.String(50), nullable=True)   # '1 year', 'Monthly', 'One-time'
    price_usd = db.Column(db.Float, nullable=False, default=0.0)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Cascade so deleting a project removes its add-ons (project_id is NOT NULL)
    project = db.relationship('Project', backref=db.backref(
        'addons', lazy=True, cascade='all, delete-orphan'))

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category, self.category)

    @property
    def category_icon(self):
        return self.CATEGORY_ICONS.get(self.category, 'fa-box')

    @property
    def status_badge_class(self):
        return self.STATUS_BADGES.get(self.status, 'bg-slate-100 text-slate-500')

    @property
    def days_until_expiry(self):
        if not self.end_date or self.status != 'active':
            return None
        return (self.end_date - date.today()).days

    @property
    def expiry_warning(self):
        d = self.days_until_expiry
        if d is None:
            return None
        if d < 0:
            return 'expired'
        if d <= 30:
            return 'urgent'
        if d <= 60:
            return 'soon'
        if d <= 90:
            return 'upcoming'
        return None


class DomainRenewal(db.Model):
    __tablename__ = 'domain_renewals'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    term_years = db.Column(db.Integer, nullable=True)
    expires_on = db.Column(db.Date, nullable=True)
    renewal_raw = db.Column(db.String(200), nullable=True)
    reminder_sent_at = db.Column(db.DateTime, nullable=True)


class ProjectStatusHistory(db.Model):
    __tablename__ = 'project_status_history'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text, nullable=True)

    changed_by = db.relationship('User', foreign_keys=[changed_by_id])

class PayrollRun(db.Model):
    """One payroll period (cutoff). Draft -> finalized (read-only) -> paid."""
    __tablename__ = 'payroll_run'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    cutoff_start = db.Column(db.Date, nullable=False)
    cutoff_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft/finalized/paid

    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    finalized_at = db.Column(db.DateTime, nullable=True)
    finalized_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)

    total_gross = db.Column(db.Float, default=0.0)
    total_deductions = db.Column(db.Float, default=0.0)
    total_net = db.Column(db.Float, default=0.0)
    employee_count = db.Column(db.Integer, default=0)

    notes = db.Column(db.Text, nullable=True)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    finalized_by = db.relationship('User', foreign_keys=[finalized_by_id])
    entries = db.relationship('PayrollEntry', backref='payroll_run', cascade='all, delete-orphan', lazy=True)

    @property
    def status_badge_class(self):
        return {
            'draft': 'bg-amber-100 text-amber-700',
            'finalized': 'bg-blue-100 text-blue-700',
            'paid': 'bg-green-100 text-green-700',
        }.get(self.status, 'bg-slate-100 text-slate-700')

    @property
    def is_editable(self):
        return self.status == 'draft'


class PayrollEntry(db.Model):
    """One employee's pay for a PayrollRun — FIXED SALARY minus deductions.

    base_pay = monthly_salary / 2 per semi-monthly cutoff (fixed at generation); time-related
    deductions (absent / late / undertime) come off gross; statutory + loan deductions off net.
    monthly_salary, daily_hours, daily_rate and hourly_rate are snapshots taken at generation.
    """
    __tablename__ = 'payroll_entry'
    id = db.Column(db.Integer, primary_key=True)
    payroll_run_id = db.Column(db.Integer, db.ForeignKey('payroll_run.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Snapshot of employee state at time of generation
    monthly_salary = db.Column(db.Float, default=0.0)  # actual monthly pay
    daily_hours = db.Column(db.Float, default=8.0)
    daily_rate = db.Column(db.Float, default=0.0)      # monthly_salary / 22
    hourly_rate = db.Column(db.Float, default=0.0)     # daily_rate / daily_hours

    # Attendance summary for the cutoff
    expected_workdays = db.Column(db.Integer, default=0)
    days_worked = db.Column(db.Float, default=0.0)
    leave_days = db.Column(db.Float, default=0.0)
    absent_days = db.Column(db.Float, default=0.0)

    # Base pay (fixed semi-monthly)
    base_pay = db.Column(db.Float, default=0.0)

    # Deductions from base (time-related)
    absent_deduction = db.Column(db.Float, default=0.0)
    late_minutes = db.Column(db.Float, default=0.0)
    late_deduction = db.Column(db.Float, default=0.0)
    undertime_hours = db.Column(db.Float, default=0.0)
    undertime_deduction = db.Column(db.Float, default=0.0)

    # Additions (OT = manual admin input for now; OT Request module in P-2)
    ot_hours_regular = db.Column(db.Float, default=0.0)
    ot_hours_restday = db.Column(db.Float, default=0.0)
    ot_pay = db.Column(db.Float, default=0.0)

    # Other earnings
    leave_pay = db.Column(db.Float, default=0.0)  # usually 0 — paid leave is already inside base pay
    allowance = db.Column(db.Float, default=0.0)
    other_earnings = db.Column(db.Float, default=0.0)

    gross_pay = db.Column(db.Float, default=0.0)

    # Government + loan deductions (manual input)
    sss = db.Column(db.Float, default=0.0)
    philhealth = db.Column(db.Float, default=0.0)
    pagibig = db.Column(db.Float, default=0.0)
    sss_loan = db.Column(db.Float, default=0.0)
    pagibig_loan = db.Column(db.Float, default=0.0)
    cash_advance = db.Column(db.Float, default=0.0)
    other_deduction = db.Column(db.Float, default=0.0)
    total_deductions = db.Column(db.Float, default=0.0)
    net_pay = db.Column(db.Float, default=0.0)

    notes = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id])

    # Manually editable numeric fields (everything else is computed by recalculate())
    INPUT_FIELDS = ('days_worked', 'absent_days', 'leave_days',
                    'base_pay', 'daily_rate', 'hourly_rate',
                    'late_minutes', 'undertime_hours',
                    'ot_hours_regular', 'ot_hours_restday',
                    'allowance', 'other_earnings', 'leave_pay',
                    'sss', 'philhealth', 'pagibig',
                    'sss_loan', 'pagibig_loan', 'cash_advance',
                    'other_deduction')

    def recalculate(self):
        """Recalculate all computed fields. base_pay stays fixed from generation."""
        # Unset columns are None until flushed; treat them as 0
        for f in self.INPUT_FIELDS:
            if getattr(self, f) is None:
                setattr(self, f, 0.0)
        minute_rate = (self.hourly_rate / 60) if self.hourly_rate else 0

        # Time-based deductions
        # Proportional to the cutoff's own workdays, so a fully absent cutoff nets exactly 0
        # (base is a fixed half-month, but cutoffs have 10-12 weekdays, not always 11)
        if self.expected_workdays and self.expected_workdays > 0:
            self.absent_deduction = round((self.absent_days / self.expected_workdays) * self.base_pay, 2)
        else:
            self.absent_deduction = 0
        self.late_deduction = round(self.late_minutes * minute_rate, 2)
        self.undertime_deduction = round(self.undertime_hours * self.hourly_rate, 2)

        # OT pay (manual input for now)
        self.ot_pay = round((self.ot_hours_regular * self.hourly_rate * 1.25) +
                            (self.ot_hours_restday * self.hourly_rate * 1.69), 2)

        # Gross: base + additions - time deductions
        self.gross_pay = round(
            self.base_pay
            + self.ot_pay
            + self.leave_pay
            + self.allowance
            + self.other_earnings
            - self.absent_deduction
            - self.late_deduction
            - self.undertime_deduction,
            2
        )

        # Statutory + loan deductions
        self.total_deductions = round(self.sss + self.philhealth + self.pagibig +
                                      self.sss_loan + self.pagibig_loan +
                                      self.cash_advance + self.other_deduction, 2)

        self.net_pay = round(self.gross_pay - self.total_deductions, 2)
