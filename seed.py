from app import app
from models import (
    db, User, Client, SalesLead, SalesInvoice,
    Project, DomainRenewal, ProjectStatusHistory,
)
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
import random

TIER_RANK = {
    'Bronze': 1, 'Essential': 1,
    'Silver': 2, 'Advanced': 2,
    'Gold': 3, 'Elite': 3,
}


def seed():
    with app.app_context():
        db.create_all()

        if User.query.first():
            print('Database already has users — skipping seed.')
            return

        # --- Users ---
        chelo = User(
            username='cheluarbuis',
            password_hash=generate_password_hash('admin@chelo1992', method='pbkdf2:sha256'),
            fname='Chilli', mname='L', lname='Arbuis', role='admin',
            job_position='Founder & Senior Web Developer',
            birthdate=date(1992, 5, 20),
            date_hired=date(2020, 1, 1),
            monthly_salary=60000.00,
            employee_type='full-time',
            employment_status='active',
        )
        employees = [
            User(username='jdoe',
                 password_hash=generate_password_hash('employee123', method='pbkdf2:sha256'),
                 fname='John', mname='A', lname='Doe', role='employee',
                 job_position='Web Developer',
                 birthdate=date(1995, 3, 12),
                 date_hired=date(2024, 6, 15),
                 monthly_salary=28000.00,
                 employee_type='full-time',
                 employment_status='active'),
            User(username='asmith',
                 password_hash=generate_password_hash('employee123', method='pbkdf2:sha256'),
                 fname='Alice', mname='M', lname='Smith', role='employee',
                 job_position='Virtual Assistant',
                 birthdate=date(1998, 9, 8),
                 date_hired=date(2025, 2, 1),
                 monthly_salary=18000.00,
                 employee_type='part-time',
                 employment_status='active'),
        ]
        db.session.add_all([chelo] + employees)
        db.session.commit()

        # --- Clients (all invented) ---
        client_names = [
            ('Margaret Chen', 'author'), ('Thomas O\'Brien', 'author'),
            ('Priya Nair', 'author'), ('David Kim', 'author'),
            ('Sarah Mendez', 'author'), ('Jacob Fletcher', 'author'),
            ('Emma Ryan', 'author'), ('Harold Vance', 'author'),
            ('Isabella Rossi', 'author'), ('Marcus Hale', 'author'),
            ('Nina Patel', 'author'), ('Oliver Grant', 'author'),
            ('Yuki Tanaka', 'author'), ('Rafael Costa', 'author'),
            ('Hannah Lee', 'author'), ('Benjamin Carr', 'author'),
            ('Sofia Alvarez', 'author'), ('James Whitmore', 'author'),
            ('Amelia Scott', 'author'), ('Victor Nguyen', 'author'),
            ('Chloe Baker', 'author'), ('Lucas Moreau', 'author'),
            ('Zoe Harrington', 'author'), ('Felix Dubois', 'author'),
            ('Ingrid Olsson', 'author'), ('Hiro Yamamoto', 'author'),
            ('Elena Petrov', 'author'), ('Oscar Blake', 'author'),
            ('Maya Johansson', 'author'), ('Diego Fernández', 'author'),
            ('Blue Mountain Press', 'company'),
            ('Northstar Publishing', 'company'),
            ('Riverstone Books', 'company'),
            ('Horizon Media Group', 'company'),
            ('Lantern Story House', 'company'),
            ('Twin Oaks Publishers', 'company'),
            ('Silverleaf Publishing', 'company'),
            ('Crescent Author Services', 'company'),
            ('Harborlight Press', 'company'),
            ('Meadowbrook Books', 'company'),
        ]
        clients = []
        for i, (name, ctype) in enumerate(client_names):
            email = name.lower().replace(' ', '.').replace("'", '') + '@example.com'
            c = Client(name=name, client_type=ctype, email=email)
            clients.append(c)
            db.session.add(c)
        db.session.commit()

        # --- Sales Leads (25) ---
        lead_specs = [
            ('Margaret Chen', 'referral', 'Website - Essential', 1500, 'new'),
            ('Thomas O\'Brien', 'web', 'Website - Advanced', 3500, 'new'),
            ('Priya Nair', 'social', 'Website - Elite', 7500, 'contacted'),
            ('David Kim', 'referral', 'Takeover', 1200, 'contacted'),
            ('Sarah Mendez', 'web', 'Website - Advanced', 3800, 'contacted'),
            ('Jacob Fletcher', 'referral', 'Website - Elite', 8200, 'quoted'),
            ('Emma Ryan', 'social', 'Website - Essential', 1800, 'quoted'),
            ('Harold Vance', 'email', 'Website - Advanced', 4200, 'quoted'),
            ('Isabella Rossi', 'referral', 'Website - Elite', 7900, 'won'),
            ('Marcus Hale', 'web', 'Website - Advanced', 3600, 'won'),
            ('Nina Patel', 'social', 'Website - Essential', 1500, 'lost'),
            ('Oliver Grant', 'referral', 'Website - Elite', 8500, 'new'),
            ('Yuki Tanaka', 'web', 'Website - Advanced', 3900, 'new'),
            ('Rafael Costa', 'referral', 'Website - Essential', 1700, 'contacted'),
            ('Hannah Lee', 'social', 'Website - Advanced', 3700, 'contacted'),
            ('Benjamin Carr', 'email', 'Website - Elite', 8000, 'quoted'),
            ('Sofia Alvarez', 'referral', 'Website - Essential', 1600, 'new'),
            ('James Whitmore', 'web', 'Website - Advanced', 4000, 'new'),
            ('Amelia Scott', 'social', 'Website - Elite', 7800, 'quoted'),
            ('Victor Nguyen', 'referral', 'Takeover', 1300, 'contacted'),
            ('Chloe Baker', 'web', 'Website - Essential', 1900, 'new'),
            ('Lucas Moreau', 'referral', 'Website - Advanced', 3500, 'won'),
            ('Zoe Harrington', 'social', 'Website - Elite', 8300, 'lost'),
            ('Felix Dubois', 'email', 'Website - Advanced', 3800, 'contacted'),
            ('Ingrid Olsson', 'web', 'Website - Essential', 1600, 'new'),
        ]
        for name, src, svc, val, status in lead_specs:
            created = datetime.now() - timedelta(days=random.randint(1, 85))
            closed = created + timedelta(days=random.randint(3, 14)) if status in ('won','lost') else None
            followup = date.today() + timedelta(days=random.randint(1, 14)) if status in ('new','contacted','quoted') else None
            email = name.lower().replace(' ', '.').replace("'", '') + '@example.com'
            db.session.add(SalesLead(
                prospect_name=name, prospect_email=email,
                source=src, service_interest=svc, estimated_value=val,
                status=status, next_followup_date=followup,
                created_at=created, closed_at=closed,
                notes=f'Lead from {src}.',
            ))

        # --- Sales Invoices (15) ---
        today = date.today()
        invoice_specs = [
            (0, 7500, 60, 'paid', 'Bank Transfer'),
            (1, 3500, 45, 'paid', 'PayPal'),
            (2, 2000, 40, 'paid', 'Wise'),
            (3, 8000, 30, 'paid', 'Bank Transfer'),
            (4, 1500, 25, 'paid', 'PayPal'),
            (5, 3800, 15, 'paid', 'Wise'),
            (6, 5000, 10, 'paid', 'Bank Transfer'),
            (7, 2500, 8, 'sent', 'Bank Transfer'),
            (8, 6500, 5, 'sent', 'PayPal'),
            (9, 1800, 3, 'sent', 'Wise'),
            (0, 1200, 50, 'paid', 'PayPal'),
            (2, 3500, 20, 'overdue', 'Bank Transfer'),
            (4, 2200, 12, 'draft', None),
            (6, 4500, 2, 'draft', None),
            (8, 1500, 90, 'paid', 'Bank Transfer'),
        ]
        for i, (ci, amt, days_ago, status, pm) in enumerate(invoice_specs, start=1):
            issue = today - timedelta(days=days_ago)
            due = issue + timedelta(days=14)
            paid = issue + timedelta(days=random.randint(1, 10)) if status == 'paid' else None
            db.session.add(SalesInvoice(
                invoice_number=f'INV-{today.year}-{i:03d}',
                client_id=clients[ci].id,
                amount=amt, issue_date=issue, due_date=due, paid_date=paid,
                payment_method=pm, status=status,
                description='Website Design Services',
            ))

        # --- Projects (50) ---
        tiers = ['Essential','Advanced','Elite','Bronze','Silver','Gold']
        statuses = ['completed','completed','completed','completed','ongoing','ongoing','lead','needs_review']
        all_devs = [chelo] + employees

        for i in range(50):
            client = clients[i % len(clients)]
            tier = random.choice(tiers)
            status = random.choice(statuses)
            domain = client.name.lower().replace(' ', '').replace("'", '').replace('.', '') + '.com'

            start = today - timedelta(days=random.randint(20, 540))
            delivered = None
            tat = None
            if status == 'completed':
                delivered = start + timedelta(days=random.randint(14, 90))
                tat = (delivered - start).days
            elif status == 'ongoing':
                start = today - timedelta(days=random.randint(5, 40))

            # Mostly assigned to Chilli, some to employees
            dev = chelo if random.random() < 0.75 else random.choice(employees)

            project = Project(
                client_id=client.id,
                domain=domain,
                service_type='takeover' if random.random() < 0.1 else 'website',
                package_tier=tier,
                tier_rank=TIER_RANK.get(tier),
                status=status,
                created_month=start.month,
                created_year=start.year,
                start_date=start,
                delivered_date=delivered,
                tat_days=tat,
                assigned_developer_id=dev.id,
                notes=f'Sample project #{i+1}.',
            )
            db.session.add(project)
            db.session.flush()  # need project.id for history

            db.session.add(ProjectStatusHistory(
                project_id=project.id, from_status=None,
                to_status=status, changed_by_id=chelo.id,
                note='Seeded',
            ))

        db.session.commit()

        print('Seeded successfully.')
        print(f'  Users:    {User.query.count()}')
        print(f'  Clients:  {Client.query.count()}')
        print(f'  Leads:    {SalesLead.query.count()}')
        print(f'  Invoices: {SalesInvoice.query.count()}')
        print(f'  Projects: {Project.query.count()}')
        print()
        print('Credentials:')
        print('  Chilli (admin) -> cheluarbuis / admin@chelo1992')
        print('  Employee       -> jdoe / employee123')


if __name__ == '__main__':
    seed()