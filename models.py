from flask import url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date

db = SQLAlchemy()


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

    edited_by = db.relationship('User', foreign_keys=[edited_by_id])

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

    marked_by = db.relationship('User', foreign_keys=[marked_by_id])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date_leave'),
    )


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