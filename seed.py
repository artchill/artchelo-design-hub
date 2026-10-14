from app import app
from models import db, User, Client, SalesLead, SalesInvoice
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
import random


def seed():
    with app.app_context():
        db.create_all()

        if User.query.first():
            print('Database already has users — skipping seed.')
            return

        # --- Users ---
        users = [
            User(username='admin',
                 password_hash=generate_password_hash('admin123', method='pbkdf2:sha256'),
                 fname='System', lname='Administrator', role='admin'),
            User(username='jdoe',
                 password_hash=generate_password_hash('employee123', method='pbkdf2:sha256'),
                 fname='John', lname='Doe', role='employee'),
            User(username='asmith',
                 password_hash=generate_password_hash('employee123', method='pbkdf2:sha256'),
                 fname='Alice', lname='Smith', role='employee'),
        ]
        db.session.add_all(users)
        db.session.commit()

        # --- Clients ---
        client_data = [
            ('Dr. R.K. Maddox', 'author', 'rkmaddox@example.com'),
            ('Andy Bott', 'author', 'andy@palaboy.com'),
            ('Judith Renfroe', 'author', 'judith@example.com'),
            ('Roger Willroth', 'author', 'roger@willrothmethod.com'),
            ('Sonny Morin', 'author', 'sonny@example.com'),
            ('Skye Elliott', 'author', 'skye@example.com'),
            ('Olympus Story House', 'company', 'contact@olympusstoryhouse.com'),
            ('Forty-Sixth Storyworks', 'company', 'hello@forty-sixthstoryworks.com'),
            ('Akari Wellness Hub', 'company', 'info@akariwellnesshub.com'),
            ('Recovery852 HK', 'company', 'hello@recovery852.com'),
        ]
        clients = []
        for name, ctype, email in client_data:
            c = Client(name=name, client_type=ctype, email=email)
            clients.append(c)
            db.session.add(c)
        db.session.commit()

        # --- Sales Leads (25) ---
        today = date.today()
        lead_names = [
            ('Margaret Chen', 'margaret@example.com', 'referral', 'Website - Essential', 1500, 'new'),
            ('Thomas O\'Brien', 'tom.obrien@example.com', 'web', 'Website - Advanced', 3500, 'new'),
            ('Priya Nair', 'priya@example.com', 'social', 'Website - Elite', 7500, 'contacted'),
            ('David Kim', 'dkim@example.com', 'referral', 'Takeover', 1200, 'contacted'),
            ('Sarah Mendez', 'smendez@example.com', 'web', 'Website - Advanced', 3800, 'contacted'),
            ('Jacob Fletcher', 'jacob@example.com', 'referral', 'Website - Elite', 8200, 'quoted'),
            ('Emma Ryan', 'emma.ryan@example.com', 'social', 'Website - Essential', 1800, 'quoted'),
            ('Harold Vance', 'harold@example.com', 'email', 'Website - Advanced', 4200, 'quoted'),
            ('Isabella Rossi', 'isabella@example.com', 'referral', 'Website - Elite', 7900, 'won'),
            ('Marcus Hale', 'marcus@example.com', 'web', 'Website - Advanced', 3600, 'won'),
            ('Nina Patel', 'nina@example.com', 'social', 'Website - Essential', 1500, 'lost'),
            ('Oliver Grant', 'ogrant@example.com', 'referral', 'Website - Elite', 8500, 'new'),
            ('Yuki Tanaka', 'yuki@example.com', 'web', 'Website - Advanced', 3900, 'new'),
            ('Rafael Costa', 'rcosta@example.com', 'referral', 'Website - Essential', 1700, 'contacted'),
            ('Hannah Lee', 'hannah@example.com', 'social', 'Website - Advanced', 3700, 'contacted'),
            ('Benjamin Carr', 'ben@example.com', 'email', 'Website - Elite', 8000, 'quoted'),
            ('Sofia Alvarez', 'sofia@example.com', 'referral', 'Website - Essential', 1600, 'new'),
            ('James Whitmore', 'james@example.com', 'web', 'Website - Advanced', 4000, 'new'),
            ('Amelia Scott', 'amelia@example.com', 'social', 'Website - Elite', 7800, 'quoted'),
            ('Victor Nguyen', 'victor@example.com', 'referral', 'Takeover', 1300, 'contacted'),
            ('Chloe Baker', 'chloe@example.com', 'web', 'Website - Essential', 1900, 'new'),
            ('Lucas Moreau', 'lucas@example.com', 'referral', 'Website - Advanced', 3500, 'won'),
            ('Zoe Harrington', 'zoe@example.com', 'social', 'Website - Elite', 8300, 'lost'),
            ('Felix Dubois', 'felix@example.com', 'email', 'Website - Advanced', 3800, 'contacted'),
            ('Ingrid Olsson', 'ingrid@example.com', 'web', 'Website - Essential', 1600, 'new'),
        ]
        for i, (name, email, src, svc, val, status) in enumerate(lead_names):
            created = datetime.now() - timedelta(days=random.randint(1, 85))
            closed = None
            if status in ('won', 'lost'):
                closed = created + timedelta(days=random.randint(3, 14))
            followup = None
            if status in ('new', 'contacted', 'quoted'):
                followup = today + timedelta(days=random.randint(1, 14))
            db.session.add(SalesLead(
                prospect_name=name, prospect_email=email,
                source=src, service_interest=svc,
                estimated_value=val, status=status,
                next_followup_date=followup,
                created_at=created, closed_at=closed,
                notes=f'Lead from {src}.',
            ))

        # --- Sales Invoices (15) ---
        invoice_specs = [
            # (client_idx, amount, days_ago_issue, status, pay_method)
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
            (0, 1200, 50, 'paid', 'PayPal'),      # repeat client
            (2, 3500, 20, 'overdue', 'Bank Transfer'),
            (4, 2200, 12, 'draft', None),
            (6, 4500, 2, 'draft', None),
            (8, 1500, 90, 'paid', 'Bank Transfer'),
        ]
        for i, (ci, amt, days_ago, status, pm) in enumerate(invoice_specs, start=1):
            issue = today - timedelta(days=days_ago)
            due = issue + timedelta(days=14)
            paid = None
            if status == 'paid':
                paid = issue + timedelta(days=random.randint(1, 10))
            inv = SalesInvoice(
                invoice_number=f'INV-{today.year}-{i:03d}',
                client_id=clients[ci].id,
                amount=amt,
                issue_date=issue,
                due_date=due,
                paid_date=paid,
                payment_method=pm,
                status=status,
                description=f'Website Design Services',
            )
            db.session.add(inv)

        db.session.commit()

        print('Seeded successfully.')
        print(f'  Users:    {User.query.count()}')
        print(f'  Clients:  {Client.query.count()}')
        print(f'  Leads:    {SalesLead.query.count()}')
        print(f'  Invoices: {SalesInvoice.query.count()}')
        print()
        print('Credentials:')
        print('  Admin    -> admin / admin123')
        print('  Employee -> jdoe / employee123')


if __name__ == '__main__':
    seed()