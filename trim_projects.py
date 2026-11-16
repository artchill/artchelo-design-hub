"""One-off data fix: replace all seeded Website Projects with 3 realistic samples.

DESTRUCTIVE: deletes every Project, AddOn, DomainRenewal and ProjectStatusHistory row.
Clients, sales leads and invoices are NOT touched.

Run once:  python trim_projects.py

Adapted to the actual schema (vs. the original spec):
  - Project has no `name`: the project is identified by its `domain` (Project.display_name)
  - `client` is a FK (client_id): clients are looked up by name, created if missing
  - `tier` is `package_tier` + `tier_rank`, stored as 'Elite'/'Advanced'/'Essential'
  - `developer_id` is `assigned_developer_id`
  - No `deadline` column: completed project gets start/delivered dates (TAT computed);
    ongoing projects get a start date and the target launch date is recorded in notes
"""
from app import app, db
from models import User, Client, Project, DomainRenewal, ProjectStatusHistory, AddOn
from datetime import date, timedelta

TIER_RANK = {'Essential': 1, 'Advanced': 2, 'Elite': 3}


def get_or_create_client(name):
    client = Client.query.filter_by(name=name).first()
    if client:
        return client, False
    client = Client(name=name, client_type='company')
    db.session.add(client)
    db.session.flush()
    return client, True


def make_project(chilli, client, domain, tier, status, start_date, notes, delivered_date=None):
    p = Project(
        client_id=client.id,
        domain=domain,
        service_type='website',
        package_tier=tier,
        tier_rank=TIER_RANK[tier],
        status=status,
        assigned_developer_id=chilli.id,
        start_date=start_date,
        created_month=start_date.month,
        created_year=start_date.year,
        delivered_date=delivered_date,
        tat_days=(delivered_date - start_date).days if delivered_date else None,
        notes=notes,
    )
    db.session.add(p)
    db.session.flush()
    # Same audit entry the app writes when a project is created
    db.session.add(ProjectStatusHistory(
        project_id=p.id, from_status=None, to_status=status,
        changed_by_id=chilli.id, note='Project created',
    ))
    return p


with app.app_context():
    chilli = User.query.filter_by(username='cheluarbuis').first()
    if not chilli:
        print('ERROR: cheluarbuis not found')
        exit(1)

    print('========== TRIMMING PROJECTS ==========')
    print()

    existing_projects = Project.query.count()
    existing_addons = AddOn.query.count()
    existing_renewals = DomainRenewal.query.count()
    existing_history = ProjectStatusHistory.query.count()

    print('Before cleanup:')
    print(f'  Projects: {existing_projects}')
    print(f'  Add-Ons: {existing_addons}')
    print(f'  Domain Renewals: {existing_renewals}')
    print(f'  Status History: {existing_history}')
    print()

    # Children first (SQLite FK enforcement is off, but keep the order safe anyway)
    print('Deleting all AddOns...')
    AddOn.query.delete()
    print('Deleting all ProjectStatusHistory...')
    ProjectStatusHistory.query.delete()
    print('Deleting all DomainRenewals...')
    DomainRenewal.query.delete()
    print('Deleting all Projects...')
    Project.query.delete()
    db.session.commit()
    print('Cleanup complete.')
    print()

    today = date.today()

    print('Clients:')
    clients = {}
    for key, name in (('akari', 'Akari Wellness and Treatment Hub'),
                      ('hub', 'Horizon Unified BPO Corp.'),
                      ('ppfdc', 'Prime Parts Fabricators & Development Corp.')):
        clients[key], created = get_or_create_client(name)
        print(f'  {"Created" if created else "Reused "}: {name}')
    print()

    print('Creating 3 sample projects...')
    hub_target = today + timedelta(days=45)
    ppfdc_target = today + timedelta(days=30)

    akari = make_project(
        chilli, clients['akari'], 'akariwellnesshub.com', 'Elite', 'completed',
        start_date=today - timedelta(days=150),
        delivered_date=today - timedelta(days=90),
        notes='Akari Wellness Hub — full Elementor Pro site for wellness and recovery services.',
    )
    hub = make_project(
        chilli, clients['hub'], 'horizonunifiedbpo.com', 'Advanced', 'ongoing',
        start_date=today - timedelta(days=30),
        notes=f'HUB BPO Website — multi-page corporate website for Cebu BPO company.\n'
              f'Target launch: {hub_target.strftime("%b %d, %Y")}',
    )
    ppfdc = make_project(
        chilli, clients['ppfdc'], 'primepartsfab.com', 'Essential', 'ongoing',
        start_date=today - timedelta(days=15),
        notes=f'PPFDC Landing Page — single-page landing site for Cebu industrial company.\n'
              f'Target launch: {ppfdc_target.strftime("%b %d, %Y")}',
    )
    db.session.commit()

    print(f'  Created: Akari Wellness Hub ({akari.domain}) — Elite / Gold, completed')
    print(f'  Created: HUB BPO Website ({hub.domain}) — Advanced / Silver, ongoing, target {hub_target}')
    print(f'  Created: PPFDC Landing Page ({ppfdc.domain}) — Essential / Bronze, ongoing, target {ppfdc_target}')
    print()

    print('Creating sample add-ons...')
    akari_addons = [
        AddOn(project_id=akari.id, name='akariwellnesshub.com domain', category='domain',
              duration_label='1 year', price_usd=12.00,
              start_date=today - timedelta(days=180), end_date=today + timedelta(days=185),
              status='active', notes='Registered via Namecheap'),
        AddOn(project_id=akari.id, name='Shared hosting (Hostinger Premium)', category='hosting',
              duration_label='1 year', price_usd=60.00,
              start_date=today - timedelta(days=180), end_date=today + timedelta(days=185),
              status='active', notes='Annual hosting plan'),
        AddOn(project_id=akari.id, name="SSL Certificate (Let's Encrypt auto-renew)", category='ssl',
              duration_label='Auto-renews every 90 days', price_usd=0.00,
              start_date=today - timedelta(days=180), end_date=None,
              status='active', notes='Free, auto-renews every 90 days'),
    ]
    hub_addons = [
        AddOn(project_id=hub.id, name='horizonunifiedbpo.com domain', category='domain',
              duration_label='1 year', price_usd=15.00,
              start_date=today - timedelta(days=30), end_date=today + timedelta(days=335),
              status='active'),
        AddOn(project_id=hub.id, name='Monthly maintenance package', category='maintenance',
              duration_label='Monthly recurring', price_usd=50.00,
              start_date=today - timedelta(days=30), end_date=None,
              status='active', notes='Monthly updates, backups, and minor edits'),
    ]
    ppfdc_addons = [
        AddOn(project_id=ppfdc.id, name='primepartsfab.com domain', category='domain',
              duration_label='2 years', price_usd=24.00,
              start_date=today - timedelta(days=15), end_date=today + timedelta(days=715),
              status='active', notes='2-year registration for cost savings'),
    ]
    db.session.add_all(akari_addons + hub_addons + ppfdc_addons)
    db.session.commit()

    total_addons = len(akari_addons) + len(hub_addons) + len(ppfdc_addons)
    print(f'  Total add-ons created: {total_addons}')
    print(f'    Akari: {len(akari_addons)} (Domain, Hosting, SSL)')
    print(f'    HUB: {len(hub_addons)} (Domain, Maintenance)')
    print(f'    PPFDC: {len(ppfdc_addons)} (Domain)')
    print()
    print('========== CLEANUP COMPLETE ==========')
    print()
    print('Final state:')
    print(f'  Projects: {Project.query.count()} (was {existing_projects})')
    print(f'  Add-Ons: {AddOn.query.count()} (was {existing_addons})')
    print(f'  Domain Renewals: {DomainRenewal.query.count()} (was {existing_renewals})')
    print(f'  Status History: {ProjectStatusHistory.query.count()} (was {existing_history})')
