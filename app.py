from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, timedelta
from calendar import monthrange, month_name
from functools import wraps
from sqlalchemy import extract, func
from models import (
    db, User, Attendance, LeaveDay,
    Client, SalesLead, SalesInvoice,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role != role:
                flash('Access denied.', 'error')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def generate_invoice_number():
    """Auto-generate the next invoice number: INV-YYYY-###"""
    year = datetime.now().year
    prefix = f'INV-{year}-'
    last = (SalesInvoice.query
            .filter(SalesInvoice.invoice_number.like(f'{prefix}%'))
            .order_by(SalesInvoice.id.desc())
            .first())
    if last:
        try:
            last_num = int(last.invoice_number.split('-')[-1])
            return f'{prefix}{last_num + 1:03d}'
        except (ValueError, IndexError):
            pass
    return f'{prefix}001'


def build_month_calendar(user_id, year, month):
    days_in_month = monthrange(year, month)[1]
    today = date.today()
    start = date(year, month, 1)
    end = date(year, month, days_in_month)

    attendances = Attendance.query.filter(
        Attendance.user_id == user_id,
        Attendance.datetime_in >= datetime.combine(start, datetime.min.time()),
        Attendance.datetime_in <= datetime.combine(end, datetime.max.time()),
    ).all()
    att_by_date = {}
    for a in attendances:
        att_by_date.setdefault(a.datetime_in.date(), []).append(a)

    leaves = LeaveDay.query.filter(
        LeaveDay.user_id == user_id,
        LeaveDay.date >= start,
        LeaveDay.date <= end,
    ).all()
    leave_by_date = {l.date: l for l in leaves}

    calendar = []
    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        is_weekend = d.weekday() >= 5
        is_future = d > today
        day_attendances = att_by_date.get(d, [])
        leave = leave_by_date.get(d)

        if day_attendances:
            status = 'present'
        elif leave:
            status = leave.leave_type.lower()
        elif is_future:
            status = 'future'
        elif is_weekend:
            status = 'no_work'
        else:
            status = 'absent'

        calendar.append({
            'date': d, 'day_name': d.strftime('%A'), 'status': status,
            'attendances': day_attendances, 'leave': leave,
            'is_future': is_future, 'is_weekend': is_weekend,
        })

    return calendar


# ---------- Auth ----------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for(
            'dashboard' if current_user.role == 'admin'
            else 'employee_dashboard'
        ))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for(
                'dashboard' if user.role == 'admin'
                else 'employee_dashboard'
            ))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------- Employee ----------

@app.route('/employee/dashboard')
@role_required('employee')
def employee_dashboard():
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))

    open_session = Attendance.query.filter_by(
        user_id=current_user.id, datetime_out=None
    ).first()
    calendar = build_month_calendar(current_user.id, year, month)

    return render_template(
        'employee_dashboard.html',
        open_session=open_session, calendar=calendar,
        year=year, month=month, month_name=month_name[month],
        available_years=range(today.year - 2, today.year + 2),
    )


@app.route('/employee/time-in', methods=['POST'])
@role_required('employee')
def time_in():
    existing = Attendance.query.filter_by(
        user_id=current_user.id, datetime_out=None
    ).first()
    if existing:
        flash('You already have an active session.', 'error')
        return redirect(url_for('employee_dashboard'))
    now = datetime.now()
    record = Attendance(
        user_id=current_user.id, datetime_in=now, day=now.strftime('%A'),
    )
    db.session.add(record)
    db.session.commit()
    flash(f'Timed in at {now.strftime("%I:%M %p")}.', 'success')
    return redirect(url_for('employee_dashboard'))


@app.route('/employee/time-out', methods=['POST'])
@role_required('employee')
def time_out():
    task_report = request.form.get('task_report', '').strip()
    if not task_report:
        flash('A task report is required to time out.', 'error')
        return redirect(url_for('employee_dashboard'))
    session_ = Attendance.query.filter_by(
        user_id=current_user.id, datetime_out=None
    ).first()
    if not session_:
        flash('No active session found.', 'error')
        return redirect(url_for('employee_dashboard'))
    now = datetime.now()
    session_.datetime_out = now
    session_.total_hours = round(
        (now - session_.datetime_in).total_seconds() / 3600, 2
    )
    session_.task_report = task_report
    db.session.commit()
    flash(f'Timed out. Total hours: {session_.total_hours}', 'success')
    return redirect(url_for('employee_dashboard'))


# ---------- Leave marking ----------

@app.route('/leave/mark', methods=['POST'])
@login_required
def mark_leave():
    target_user_id = int(request.form.get('user_id', current_user.id))
    date_str = request.form.get('date', '').strip()
    leave_type = request.form.get('leave_type', '').strip().upper()
    note = request.form.get('note', '').strip()
    redirect_to = request.form.get('redirect_to', 'employee_dashboard')
    redirect_kwargs = {}
    if redirect_to == 'admin_employee_tracker':
        redirect_kwargs['employee_id'] = target_user_id
        redirect_kwargs['year'] = request.form.get('year')
        redirect_kwargs['month'] = request.form.get('month')

    if current_user.role != 'admin' and target_user_id != current_user.id:
        flash('You can only mark leave for yourself.', 'error')
        return redirect(url_for(redirect_to, **redirect_kwargs))
    if leave_type not in ('VL', 'SL'):
        flash('Leave type must be VL or SL.', 'error')
        return redirect(url_for(redirect_to, **redirect_kwargs))
    try:
        leave_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date.', 'error')
        return redirect(url_for(redirect_to, **redirect_kwargs))

    has_att = Attendance.query.filter(
        Attendance.user_id == target_user_id,
        Attendance.datetime_in >= datetime.combine(leave_date, datetime.min.time()),
        Attendance.datetime_in <= datetime.combine(leave_date, datetime.max.time()),
    ).first()
    if has_att:
        flash('Cannot mark leave — attendance already recorded.', 'error')
        return redirect(url_for(redirect_to, **redirect_kwargs))

    existing = LeaveDay.query.filter_by(
        user_id=target_user_id, date=leave_date
    ).first()
    if existing:
        existing.leave_type = leave_type
        existing.note = note or None
        existing.marked_by_id = current_user.id
        existing.marked_at = datetime.now()
        flash(f'Updated {leave_date} to {leave_type}.', 'success')
    else:
        new_leave = LeaveDay(
            user_id=target_user_id, date=leave_date,
            leave_type=leave_type, note=note or None,
            marked_by_id=current_user.id,
        )
        db.session.add(new_leave)
        flash(f'Marked {leave_date} as {leave_type}.', 'success')
    db.session.commit()
    return redirect(url_for(redirect_to, **redirect_kwargs))


@app.route('/leave/<int:leave_id>/delete', methods=['POST'])
@login_required
def delete_leave(leave_id):
    leave = LeaveDay.query.get_or_404(leave_id)
    if current_user.role != 'admin' and leave.user_id != current_user.id:
        flash('Not allowed.', 'error')
        return redirect(url_for('employee_dashboard'))
    redirect_to = request.form.get('redirect_to', 'employee_dashboard')
    redirect_kwargs = {}
    if redirect_to == 'admin_employee_tracker':
        redirect_kwargs['employee_id'] = leave.user_id
        redirect_kwargs['year'] = request.form.get('year')
        redirect_kwargs['month'] = request.form.get('month')
    db.session.delete(leave)
    db.session.commit()
    flash('Leave entry removed.', 'success')
    return redirect(url_for(redirect_to, **redirect_kwargs))


# ---------- Admin: Attendance ----------

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    first_employee = User.query.filter_by(role='employee').order_by(User.fname).first()
    if first_employee:
        return redirect(url_for('admin_employee_tracker',
                                employee_id=first_employee.id))
    return render_template('admin_dashboard_empty.html')


@app.route('/admin/employees/<int:employee_id>/tracker')
@role_required('admin')
def admin_employee_tracker(employee_id):
    employee = User.query.get_or_404(employee_id)
    today = date.today()
    year = int(request.args.get('year', today.year))
    month = int(request.args.get('month', today.month))
    calendar = build_month_calendar(employee_id, year, month)
    all_employees = User.query.filter_by(role='employee').order_by(User.fname).all()
    return render_template(
        'admin_employee_tracker.html',
        employee=employee, all_employees=all_employees, calendar=calendar,
        year=year, month=month, month_name=month_name[month],
        available_years=range(today.year - 2, today.year + 2),
    )


@app.route('/admin/employees')
@role_required('admin')
def admin_employees():
    employees = User.query.filter_by(role='employee').all()
    return render_template('admin_employees.html', employees=employees)


@app.route('/admin/employees/new', methods=['GET', 'POST'])
@role_required('admin')
def admin_new_employee():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        fname = request.form.get('fname', '').strip()
        lname = request.form.get('lname', '').strip()
        role = request.form.get('role', '').strip()
        errors = []
        if not username or not password or not fname or not lname or not role:
            errors.append('All fields are required.')
        if role not in ('employee', 'admin'):
            errors.append('Invalid role selected.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if User.query.filter_by(username=username).first():
            errors.append(f'Username "{username}" is already taken.')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin_new_employee.html',
                form_data={'username': username, 'fname': fname,
                           'lname': lname, 'role': role})
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
            fname=fname, lname=lname, role=role,
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'User "{username}" created successfully.', 'success')
        return redirect(url_for('admin_employees'))
    return render_template('admin_new_employee.html', form_data={})


@app.route('/admin/attendance/<int:record_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def admin_edit_attendance(record_id):
    record = Attendance.query.get_or_404(record_id)
    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        time_in_str = request.form.get('time_in', '').strip()
        time_out_str = request.form.get('time_out', '').strip()
        task_report = request.form.get('task_report', '').strip()
        errors = []
        if not date_str or not time_in_str:
            errors.append('Date and Time In are required.')
        new_datetime_in = None
        new_datetime_out = None
        if not errors:
            try:
                new_datetime_in = datetime.strptime(
                    f'{date_str} {time_in_str}', '%Y-%m-%d %H:%M')
            except ValueError:
                errors.append('Invalid Date or Time In format.')
        if time_out_str and not errors:
            try:
                new_datetime_out = datetime.strptime(
                    f'{date_str} {time_out_str}', '%Y-%m-%d %H:%M')
                if new_datetime_out <= new_datetime_in:
                    errors.append('Time Out must be after Time In.')
            except ValueError:
                errors.append('Invalid Time Out format.')
        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admin_edit_attendance.html', record=record)
        record.datetime_in = new_datetime_in
        record.day = new_datetime_in.strftime('%A')
        if new_datetime_out:
            record.datetime_out = new_datetime_out
            record.total_hours = round(
                (new_datetime_out - new_datetime_in).total_seconds() / 3600, 2)
        else:
            record.datetime_out = None
            record.total_hours = None
        record.task_report = task_report or None
        record.edited_at = datetime.now()
        record.edited_by_id = current_user.id
        db.session.commit()
        flash('Attendance record updated successfully.', 'success')
        return redirect(url_for('admin_employee_tracker',
                                employee_id=record.user_id))
    return render_template('admin_edit_attendance.html', record=record)


# ========== SALES MODULE ==========

@app.route('/sales')
@role_required('admin')
def sales_overview():
    today = date.today()
    month_start = date(today.year, today.month, 1)

    pipeline_value = db.session.query(func.sum(SalesLead.estimated_value)).filter(
        SalesLead.status.in_(('new', 'contacted', 'quoted'))
    ).scalar() or 0

    revenue_this_month = db.session.query(func.sum(SalesInvoice.amount)).filter(
        SalesInvoice.status == 'paid',
        SalesInvoice.paid_date >= month_start,
    ).scalar() or 0

    outstanding = db.session.query(func.sum(SalesInvoice.amount)).filter(
        SalesInvoice.status.in_(('sent', 'overdue'))
    ).scalar() or 0

    leads_won_month = SalesLead.query.filter(
        SalesLead.status == 'won',
        SalesLead.closed_at >= datetime.combine(month_start, datetime.min.time())
    ).count()

    recent_leads = SalesLead.query.order_by(SalesLead.created_at.desc()).limit(5).all()
    recent_invoices = SalesInvoice.query.order_by(SalesInvoice.issue_date.desc()).limit(5).all()

    return render_template(
        'sales_overview.html',
        pipeline_value=pipeline_value,
        revenue_this_month=revenue_this_month,
        outstanding=outstanding,
        leads_won_month=leads_won_month,
        recent_leads=recent_leads,
        recent_invoices=recent_invoices,
    )


# ----- Leads CRUD -----

@app.route('/sales/leads')
@role_required('admin')
def sales_leads():
    status_filter = request.args.get('status', '')
    query = SalesLead.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    leads = query.order_by(SalesLead.created_at.desc()).all()
    return render_template('sales_leads.html', leads=leads, status_filter=status_filter)


@app.route('/sales/leads/new', methods=['GET', 'POST'])
@role_required('admin')
def sales_lead_new():
    if request.method == 'POST':
        lead = SalesLead(
            prospect_name=request.form.get('prospect_name', '').strip(),
            prospect_email=request.form.get('prospect_email', '').strip() or None,
            prospect_phone=request.form.get('prospect_phone', '').strip() or None,
            source=request.form.get('source', '').strip() or None,
            service_interest=request.form.get('service_interest', '').strip() or None,
            estimated_value=float(request.form.get('estimated_value') or 0) or None,
            status=request.form.get('status', 'new'),
            notes=request.form.get('notes', '').strip() or None,
        )
        followup = request.form.get('next_followup_date', '').strip()
        if followup:
            try:
                lead.next_followup_date = datetime.strptime(followup, '%Y-%m-%d').date()
            except ValueError:
                pass
        if not lead.prospect_name:
            flash('Prospect name is required.', 'error')
            return render_template('sales_lead_form.html', lead=lead, is_new=True)
        db.session.add(lead)
        db.session.commit()
        flash('Lead created.', 'success')
        return redirect(url_for('sales_leads'))
    return render_template('sales_lead_form.html', lead=None, is_new=True)


@app.route('/sales/leads/<int:lead_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def sales_lead_edit(lead_id):
    lead = SalesLead.query.get_or_404(lead_id)
    if request.method == 'POST':
        lead.prospect_name = request.form.get('prospect_name', '').strip()
        lead.prospect_email = request.form.get('prospect_email', '').strip() or None
        lead.prospect_phone = request.form.get('prospect_phone', '').strip() or None
        lead.source = request.form.get('source', '').strip() or None
        lead.service_interest = request.form.get('service_interest', '').strip() or None
        lead.estimated_value = float(request.form.get('estimated_value') or 0) or None
        new_status = request.form.get('status', 'new')
        if new_status in ('won', 'lost') and lead.status not in ('won', 'lost'):
            lead.closed_at = datetime.now()
        lead.status = new_status
        lead.notes = request.form.get('notes', '').strip() or None
        followup = request.form.get('next_followup_date', '').strip()
        if followup:
            try:
                lead.next_followup_date = datetime.strptime(followup, '%Y-%m-%d').date()
            except ValueError:
                lead.next_followup_date = None
        else:
            lead.next_followup_date = None
        db.session.commit()
        flash('Lead updated.', 'success')
        return redirect(url_for('sales_leads'))
    return render_template('sales_lead_form.html', lead=lead, is_new=False)


@app.route('/sales/leads/<int:lead_id>/delete', methods=['POST'])
@role_required('admin')
def sales_lead_delete(lead_id):
    lead = SalesLead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted.', 'success')
    return redirect(url_for('sales_leads'))


# ----- Invoices CRUD -----

@app.route('/sales/invoices')
@role_required('admin')
def sales_invoices():
    status_filter = request.args.get('status', '')
    query = SalesInvoice.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    invoices = query.order_by(SalesInvoice.issue_date.desc()).all()
    return render_template('sales_invoices.html', invoices=invoices, status_filter=status_filter)


@app.route('/sales/invoices/new', methods=['GET', 'POST'])
@role_required('admin')
def sales_invoice_new():
    clients = Client.query.order_by(Client.name).all()
    if request.method == 'POST':
        client_id = int(request.form.get('client_id', 0) or 0)
        amount = float(request.form.get('amount') or 0)
        issue_date_str = request.form.get('issue_date', '').strip()
        if not client_id or amount <= 0 or not issue_date_str:
            flash('Client, amount, and issue date are required.', 'error')
            return render_template('sales_invoice_form.html',
                                   invoice=None, clients=clients, is_new=True)
        try:
            issue_dt = datetime.strptime(issue_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid issue date.', 'error')
            return render_template('sales_invoice_form.html',
                                   invoice=None, clients=clients, is_new=True)

        due_date_str = request.form.get('due_date', '').strip()
        due_dt = None
        if due_date_str:
            try:
                due_dt = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        invoice = SalesInvoice(
            invoice_number=generate_invoice_number(),
            client_id=client_id,
            amount=amount,
            issue_date=issue_dt,
            due_date=due_dt,
            payment_method=request.form.get('payment_method', '').strip() or None,
            status=request.form.get('status', 'draft'),
            description=request.form.get('description', '').strip() or None,
            notes=request.form.get('notes', '').strip() or None,
        )
        db.session.add(invoice)
        db.session.commit()
        flash(f'Invoice {invoice.invoice_number} created.', 'success')
        return redirect(url_for('sales_invoices'))
    return render_template('sales_invoice_form.html',
                           invoice=None, clients=clients, is_new=True)


@app.route('/sales/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def sales_invoice_edit(invoice_id):
    invoice = SalesInvoice.query.get_or_404(invoice_id)
    clients = Client.query.order_by(Client.name).all()
    if request.method == 'POST':
        invoice.client_id = int(request.form.get('client_id', invoice.client_id))
        invoice.amount = float(request.form.get('amount') or invoice.amount)
        issue_date_str = request.form.get('issue_date', '').strip()
        if issue_date_str:
            try:
                invoice.issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        due_date_str = request.form.get('due_date', '').strip()
        if due_date_str:
            try:
                invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                invoice.due_date = None
        else:
            invoice.due_date = None

        new_status = request.form.get('status', invoice.status)
        if new_status == 'paid' and invoice.status != 'paid':
            paid_date_str = request.form.get('paid_date', '').strip()
            if paid_date_str:
                try:
                    invoice.paid_date = datetime.strptime(paid_date_str, '%Y-%m-%d').date()
                except ValueError:
                    invoice.paid_date = date.today()
            else:
                invoice.paid_date = date.today()
        elif new_status != 'paid':
            invoice.paid_date = None
        invoice.status = new_status

        invoice.payment_method = request.form.get('payment_method', '').strip() or None
        invoice.description = request.form.get('description', '').strip() or None
        invoice.notes = request.form.get('notes', '').strip() or None

        db.session.commit()
        flash(f'Invoice {invoice.invoice_number} updated.', 'success')
        return redirect(url_for('sales_invoices'))
    return render_template('sales_invoice_form.html',
                           invoice=invoice, clients=clients, is_new=False)


@app.route('/sales/invoices/<int:invoice_id>/delete', methods=['POST'])
@role_required('admin')
def sales_invoice_delete(invoice_id):
    invoice = SalesInvoice.query.get_or_404(invoice_id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted.', 'success')
    return redirect(url_for('sales_invoices'))


# ----- Clients CRUD -----

@app.route('/sales/clients')
@role_required('admin')
def sales_clients():
    clients = Client.query.order_by(Client.name).all()
    return render_template('sales_clients.html', clients=clients)


@app.route('/sales/clients/new', methods=['GET', 'POST'])
@role_required('admin')
def sales_client_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Client name is required.', 'error')
            return render_template('sales_client_form.html', client=None, is_new=True)
        client = Client(
            name=name,
            client_type=request.form.get('client_type', 'author'),
            email=request.form.get('email', '').strip() or None,
            phone=request.form.get('phone', '').strip() or None,
            notes=request.form.get('notes', '').strip() or None,
        )
        db.session.add(client)
        db.session.commit()
        flash(f'Client "{client.name}" added.', 'success')
        return redirect(url_for('sales_clients'))
    return render_template('sales_client_form.html', client=None, is_new=True)


@app.route('/sales/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def sales_client_edit(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        client.name = request.form.get('name', '').strip() or client.name
        client.client_type = request.form.get('client_type', client.client_type)
        client.email = request.form.get('email', '').strip() or None
        client.phone = request.form.get('phone', '').strip() or None
        client.notes = request.form.get('notes', '').strip() or None
        db.session.commit()
        flash('Client updated.', 'success')
        return redirect(url_for('sales_clients'))
    return render_template('sales_client_form.html', client=client, is_new=False)


@app.route('/sales/clients/<int:client_id>/delete', methods=['POST'])
@role_required('admin')
def sales_client_delete(client_id):
    client = Client.query.get_or_404(client_id)
    if client.invoices:
        flash(f'Cannot delete {client.name} — client has invoices.', 'error')
        return redirect(url_for('sales_clients'))
    db.session.delete(client)
    db.session.commit()
    flash('Client deleted.', 'success')
    return redirect(url_for('sales_clients'))


# ========== MAIN DASHBOARD ==========

@app.route('/dashboard')
@role_required('admin')
def dashboard():
    """Artchelo Design main dashboard — admin landing page."""
    today = date.today()
    month_start = date(today.year, today.month, 1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # ---- KPIs ----
    revenue_this_month = db.session.query(func.sum(SalesInvoice.amount)).filter(
        SalesInvoice.status == 'paid',
        SalesInvoice.paid_date >= month_start,
    ).scalar() or 0

    revenue_last_month = db.session.query(func.sum(SalesInvoice.amount)).filter(
        SalesInvoice.status == 'paid',
        SalesInvoice.paid_date >= last_month_start,
        SalesInvoice.paid_date < month_start,
    ).scalar() or 0

    pipeline_value = db.session.query(func.sum(SalesLead.estimated_value)).filter(
        SalesLead.status.in_(('new', 'contacted', 'quoted'))
    ).scalar() or 0

    outstanding = db.session.query(func.sum(SalesInvoice.amount)).filter(
        SalesInvoice.status.in_(('sent', 'overdue'))
    ).scalar() or 0

    active_clients = Client.query.count()

    leads_won_month = SalesLead.query.filter(
        SalesLead.status == 'won',
        SalesLead.closed_at >= datetime.combine(month_start, datetime.min.time())
    ).count()

    open_leads = SalesLead.query.filter(
        SalesLead.status.in_(('new', 'contacted', 'quoted'))
    ).count()

    # ---- Chart 1: Revenue trend (last 6 months) ----
    revenue_trend_labels = []
    revenue_trend_data = []
    for i in range(5, -1, -1):
        m = (month_start - timedelta(days=i * 30)).replace(day=1)
        next_m = (m + timedelta(days=32)).replace(day=1)
        rev = db.session.query(func.sum(SalesInvoice.amount)).filter(
            SalesInvoice.status == 'paid',
            SalesInvoice.paid_date >= m,
            SalesInvoice.paid_date < next_m,
        ).scalar() or 0
        revenue_trend_labels.append(m.strftime('%b %Y'))
        revenue_trend_data.append(float(rev))

    # ---- Chart 2: Sales Funnel ----
    funnel_data = {
        'new': SalesLead.query.filter_by(status='new').count(),
        'contacted': SalesLead.query.filter_by(status='contacted').count(),
        'quoted': SalesLead.query.filter_by(status='quoted').count(),
        'won': SalesLead.query.filter_by(status='won').count(),
        'lost': SalesLead.query.filter_by(status='lost').count(),
    }

    # ---- Chart 3: Invoice Status Breakdown ----
    invoice_status = {
        'draft': SalesInvoice.query.filter_by(status='draft').count(),
        'sent': SalesInvoice.query.filter_by(status='sent').count(),
        'paid': SalesInvoice.query.filter_by(status='paid').count(),
        'overdue': SalesInvoice.query.filter_by(status='overdue').count(),
        'void': SalesInvoice.query.filter_by(status='void').count(),
    }

    # ---- Chart 4: Leads by Source ----
    sources_query = db.session.query(
        SalesLead.source, func.count(SalesLead.id)
    ).group_by(SalesLead.source).all()
    sources_data = {s or 'Unknown': c for s, c in sources_query}

    # ---- Chart 5: Top Clients by Revenue ----
    top_clients_query = db.session.query(
        Client.name, func.sum(SalesInvoice.amount)
    ).join(SalesInvoice, SalesInvoice.client_id == Client.id).filter(
        SalesInvoice.status == 'paid'
    ).group_by(Client.name).order_by(func.sum(SalesInvoice.amount).desc()).limit(5).all()
    top_clients_labels = [name for name, _ in top_clients_query]
    top_clients_data = [float(amt) for _, amt in top_clients_query]

    # ---- Recent activity ----
    recent_leads = SalesLead.query.order_by(SalesLead.created_at.desc()).limit(5).all()
    recent_invoices = SalesInvoice.query.order_by(SalesInvoice.issue_date.desc()).limit(5).all()

    # ---- Upcoming follow-ups ----
    upcoming_followups = SalesLead.query.filter(
        SalesLead.next_followup_date != None,
        SalesLead.next_followup_date >= today,
        SalesLead.next_followup_date <= today + timedelta(days=7),
        SalesLead.status.in_(('new', 'contacted', 'quoted')),
    ).order_by(SalesLead.next_followup_date).all()

    return render_template(
        'dashboard.html',
        revenue_this_month=revenue_this_month,
        revenue_last_month=revenue_last_month,
        pipeline_value=pipeline_value,
        outstanding=outstanding,
        active_clients=active_clients,
        leads_won_month=leads_won_month,
        open_leads=open_leads,
        revenue_trend_labels=revenue_trend_labels,
        revenue_trend_data=revenue_trend_data,
        funnel_data=funnel_data,
        invoice_status=invoice_status,
        sources_data=sources_data,
        top_clients_labels=top_clients_labels,
        top_clients_data=top_clients_data,
        recent_leads=recent_leads,
        recent_invoices=recent_invoices,
        upcoming_followups=upcoming_followups,
        current_month_name=today.strftime('%B %Y'),
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)