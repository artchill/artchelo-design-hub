from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fname = db.Column(db.String(80), nullable=False)
    lname = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendances = db.relationship(
        'Attendance',
        foreign_keys='Attendance.user_id',
        backref='user',
        lazy=True,
    )
    leave_days = db.relationship(
        'LeaveDay',
        foreign_keys='LeaveDay.user_id',
        backref='user',
        lazy=True,
    )


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


# ========== NEW: Sales & Clients ==========

class Client(db.Model):
    """A customer — individual author or company."""
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    client_type = db.Column(db.String(20), default='author')  # author / company / other
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leads = db.relationship('SalesLead', backref='client', lazy=True)
    invoices = db.relationship('SalesInvoice', backref='client', lazy=True)


class SalesLead(db.Model):
    """A sales opportunity — potential client who hasn't bought yet."""
    __tablename__ = 'sales_leads'
    id = db.Column(db.Integer, primary_key=True)
    prospect_name = db.Column(db.String(200), nullable=False)
    prospect_email = db.Column(db.String(200), nullable=True)
    prospect_phone = db.Column(db.String(50), nullable=True)
    source = db.Column(db.String(50), nullable=True)  # referral / web / social / other
    service_interest = db.Column(db.String(100), nullable=True)
    estimated_value = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='new')  # new/contacted/quoted/won/lost
    next_followup_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    # If a lead was converted to a client
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)


class SalesInvoice(db.Model):
    """A billable invoice to a client."""
    __tablename__ = 'sales_invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    paid_date = db.Column(db.Date, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='draft')  # draft/sent/paid/overdue/void
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)