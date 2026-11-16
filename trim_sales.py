"""One-off data fix: trim the Sales module to 3 clients, 3 leads, 3 invoices.

DESTRUCTIVE: deletes every SalesInvoice and SalesLead, and every Client that no
Website Project points at. Run once:  python trim_sales.py

Adapted to the actual schema (vs. the original spec):
  - Clients referenced by Website Projects are KEPT and updated in place (deleting
    them would orphan the 3 projects, whose client_id is NOT NULL)
  - Client has no contact_person/company columns: contact person goes into notes;
    client_type='company'
  - SalesLead columns are prospect_name / prospect_email / prospect_phone; contact
    person goes into notes. Status 'qualified' doesn't exist -> 'quoted'.
    Sources use the form's values: 'web' (contact form), 'referral', 'social' (LinkedIn)
  - SalesInvoice.issue_date is NOT NULL, so the draft invoice is dated today
"""
from app import app, db
from models import User, Client, SalesLead, SalesInvoice, Project
from datetime import datetime, date, timedelta


def upsert_client(name, **fields):
    client = Client.query.filter_by(name=name).first()
    created = client is None
    if created:
        client = Client(name=name)
        db.session.add(client)
    for key, value in fields.items():
        setattr(client, key, value)
    db.session.flush()
    return client, created


with app.app_context():
    chilli = User.query.filter_by(username='cheluarbuis').first()
    if not chilli:
        print('ERROR: cheluarbuis not found')
        exit(1)

    print('========== TRIMMING SALES MODULE ==========')
    print()

    before_clients = Client.query.count()
    before_leads = SalesLead.query.count()
    before_invoices = SalesInvoice.query.count()
    print('Before cleanup:')
    print(f'  Clients: {before_clients}')
    print(f'  Leads: {before_leads}')
    print(f'  Invoices: {before_invoices}')
    print()

    # Delete in dependency order: invoices -> leads -> clients (except project clients)
    project_client_ids = {cid for (cid,) in db.session.query(Project.client_id).distinct()}
    print('Deleting all invoices...')
    SalesInvoice.query.delete()
    print('Deleting all leads...')
    SalesLead.query.delete()
    print(f'Deleting clients not linked to a Website Project (keeping {len(project_client_ids)})...')
    removed = Client.query.filter(Client.id.notin_(project_client_ids)).delete(synchronize_session=False)
    db.session.commit()
    print(f'Cleanup complete ({removed} clients removed).')
    print()

    today = date.today()

    print('Setting up 3 sample clients...')
    akari, c1 = upsert_client(
        'Akari Wellness and Treatment Hub', client_type='company',
        email='contact@akariwellnesshub.com', phone='+852 2555 0100',
        notes='Contact: Jennifer Chan\nWellness and recovery services in Hong Kong. Elite tier client.',
    )
    hub, c2 = upsert_client(
        'Horizon Unified BPO Corp.', client_type='company',
        email='mark@horizonunifiedbpo.com', phone='+63 32 123 4567',
        notes='Contact: Mark Reyes\nCebu-based BPO company. Advanced tier. Current ongoing project.',
    )
    ppfdc, c3 = upsert_client(
        'Prime Parts Fabricators & Development Corp.', client_type='company',
        email='info@primepartsfab.com', phone='+63 32 234 5678',
        notes='Contact: Engr. Roberto Santos (Prime Parts Fabricators)\n'
              'Cebu industrial fabrication company. Essential tier. Landing page project.',
    )
    db.session.commit()
    for c, created in ((akari, c1), (hub, c2), (ppfdc, c3)):
        print(f'  {"Created" if created else "Updated"}: {c.name} (#{c.id}, {len(c.projects)} project)')
    print()

    print('Creating 3 sample leads...')
    lead_new = SalesLead(
        prospect_name="Sarah's Coffee Shop",
        prospect_email='sarah@sarahscoffee.ph',
        prospect_phone='+63 917 123 4567',
        source='web',
        service_interest='Website - Essential',
        estimated_value=800.00,
        status='new',
        next_followup_date=today + timedelta(days=2),
        notes='Contact: Sarah Villamor (via contact form)\n'
              'Inquired about a simple one-page site for her cafe. Needs online menu.',
    )
    lead_quoted = SalesLead(
        prospect_name='Davao Marketing Agency',
        prospect_email='mike@davaomarketing.com',
        prospect_phone='+63 918 234 5678',
        source='referral',
        service_interest='Website - Elite',
        estimated_value=2500.00,
        status='quoted',
        next_followup_date=today + timedelta(days=5),
        notes='Contact: Michael Tan\nHad initial meeting. Awaiting decision on Elite package proposal.',
    )
    lead_won = SalesLead(
        prospect_name='Horizon Unified BPO Corp.',
        prospect_email='mark@horizonunifiedbpo.com',
        prospect_phone='+63 32 123 4567',
        source='social',
        service_interest='Website - Advanced',
        estimated_value=1800.00,
        status='won',
        client_id=hub.id,
        closed_at=datetime.combine(today - timedelta(days=35), datetime.min.time()),
        notes='Contact: Mark Reyes (via LinkedIn)\nConverted to client. Advanced package signed. Project ongoing.',
    )
    db.session.add_all([lead_new, lead_quoted, lead_won])
    db.session.commit()
    print(f'  Created: {lead_new.prospect_name} (NEW)')
    print(f'  Created: {lead_quoted.prospect_name} (QUOTED)')
    print(f'  Created: {lead_won.prospect_name} (WON -> client #{hub.id})')
    print()

    print('Creating 3 sample invoices...')
    inv_paid = SalesInvoice(
        client_id=akari.id,
        invoice_number='INV-2026-001',
        amount=2500.00,
        status='paid',
        issue_date=today - timedelta(days=120),
        due_date=today - timedelta(days=90),
        paid_date=today - timedelta(days=85),
        payment_method='Bank Transfer',
        description='Elite Package - Akari Wellness Hub full Elementor Pro site.',
    )
    inv_sent = SalesInvoice(
        client_id=hub.id,
        invoice_number='INV-2026-002',
        amount=1800.00,
        status='sent',
        issue_date=today - timedelta(days=30),
        due_date=today + timedelta(days=15),
        description='Advanced Package - HUB BPO multi-page website (50% deposit).',
    )
    inv_draft = SalesInvoice(
        client_id=ppfdc.id,
        invoice_number='INV-2026-003',
        amount=800.00,
        status='draft',
        issue_date=today,   # NOT NULL column; update when actually sent
        description='Essential Package - PPFDC landing page (pending client sign-off).',
    )
    db.session.add_all([inv_paid, inv_sent, inv_draft])
    db.session.commit()
    for inv in (inv_paid, inv_sent, inv_draft):
        print(f'  Created: {inv.invoice_number} - ${inv.amount:,.2f} ({inv.status.upper()}) -> {inv.client.name}')
    print()

    print('========== SALES CLEANUP COMPLETE ==========')
    print()
    print('Final state:')
    print(f'  Clients: {Client.query.count()} (was {before_clients})')
    print(f'  Leads: {SalesLead.query.count()} (was {before_leads})')
    print(f'  Invoices: {SalesInvoice.query.count()} (was {before_invoices})')
    print(f'  Projects (untouched): {Project.query.count()}, all with a client: '
          f'{all(p.client is not None for p in Project.query.all())}')
