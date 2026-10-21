# Artchelo Design Business Hub — Developer Guide

Complete setup, workflow, and reference guide for working on this Flask app across Mac and Windows.

---

## 📋 Project Info

- **Name:** Artchelo Design Business Hub
- **Owner:** Chilli (Richellou L. Arbuis) — Artchelo Design, Cebu, Philippines
- **Stack:** Flask 3.0 + SQLite + Jinja2 + Tailwind CSS (CDN) + Chart.js + SweetAlert2
- **Repo:** https://github.com/artchill/artchelo-design-hub
- **Working branch:** `expansion` (not `main`)
- **Local port:** 5001 (macOS AirPlay blocks 5000)

---

## 🔐 Credentials

### Admin
- Username: `cheluarbuis`
- Password: `admin@chelo1992`

### Employees (test accounts)
- `jdoe` / `employee123`
- `asmith` / `employee123`

---

## 💻 First-Time Setup

### Mac
```bash
cd ~/Desktop
git clone -b expansion https://github.com/artchill/artchelo-design-hub.git
cd artchelo-design-hub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 seed.py
python3 app.py
```

### Windows
```powershell
cd C:\
mkdir Projects
cd Projects
git clone -b expansion https://github.com/artchill/artchelo-design-hub.git
cd artchelo-design-hub
python -m venv venv

# One-time fix for PowerShell script policy
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python app.py
```

Open browser → **http://localhost:5001** → login as `cheluarbuis` / `admin@chelo1992`.

---

## 🔄 Daily Workflow

### Starting a session (ALWAYS pull first)

**Mac:**
```bash
cd ~/Desktop/artchelo-design-hub
git pull
source venv/bin/activate
python3 app.py
```

**Windows:**
```powershell
cd C:\Projects\artchelo-design-hub
git pull
venv\Scripts\activate
python app.py
```

### Ending a session (ALWAYS push before switching devices)



### Golden Rule
🏆 **ALWAYS `git pull` first. ALWAYS `git push` last.** Prevents merge conflicts between Mac and Windows.

---

## 🖥️ Mac vs Windows Command Reference

| Task | Mac | Windows |
|---|---|---|
| Python command | `python3` | `python` |
| Activate venv | `source venv/bin/activate` | `venv\Scripts\activate` |
| Delete folder | `rm -rf instance` | `Remove-Item -Recurse -Force instance` |
| Path separator | `/` | `\` |
| Terminal | Terminal.app / zsh | PowerShell |

---

## ⚠️ Cross-Platform Code Rules

### Date formatting — AVOID these Mac-only format codes:
- ❌ `%-d` (fails on Windows)
- ❌ `%-m`
- ❌ `%-H`
- ❌ `%-I`

### Instead, use cross-platform patterns:
```python
# Instead of: date.strftime('%b %-d')  (May 5 on Mac, FAILS on Windows)
date.strftime('%b %d').lstrip('0').replace(' 0', ' ')

# Instead of: date.strftime('%B %-d, %Y')  (May 5, 2026 on Mac, FAILS on Windows)
date.strftime('%B %d, %Y').replace(' 0', ' ')
```

### Line endings
Git may show "LF will be replaced by CRLF" warnings on Windows. Safe to ignore — Git normalizes automatically.

To silence warnings on Windows:
```powershell
git config --global core.autocrlf true
```

---

## 🏗️ Project Structure



---

## 🗄️ Database Schema

### User
Core identity + profile fields.
- `id`, `username`, `password_hash`, `fname`, `mname`, `lname`, `role`, `created_at`
- Profile: `job_position`, `birthdate`, `date_hired`, `monthly_salary` (PHP ₱), `employee_type` (full-time/part-time/outsourced), `employment_status` (active/on_leave/resigned/terminated), `resignation_date`
- Computed properties: `age`, `full_name` ("First M. Last"), `initials`, `is_active_employee`

### Attendance
Employee time-in/out records with audit trail.
- `id`, `user_id`, `datetime_in`, `datetime_out`, `total_hours`, `day`, `task_report`
- Audit: `edited_at`, `edited_by_id`

### LeaveDay
Admin or self-marked VL / SL days.
- `id`, `user_id`, `date`, `leave_type` (VL/SL), `note`, `marked_by_id`, `marked_at`

### Client
Customers.
- `id`, `name`, `client_type`, `email`, `phone`, `notes`, `created_at`

### SalesLead
Prospects in the sales funnel.
- `id`, `prospect_name`, `email`, `phone`, `source`, `service_interest`, `estimated_value` (USD $), `status` (new/contacted/quoted/won/lost), `notes`, `next_followup_date`, `created_at`, `closed_at`

### SalesInvoice
Billing records.
- `id`, `invoice_number`, `client_id`, `amount` (USD $), `issue_date`, `due_date`, `paid_date`, `payment_method`, `status` (draft/sent/paid/overdue/void), `description`, `notes`

### Project
Website build engagements.
- `id`, `client_id`, `domain`, `service_type` (website/takeover), `package_tier` (Bronze/Silver/Gold or Essential/Advanced/Elite), `tier_rank`, `status` (lead/ongoing/completed/on_hold/cancelled), `assigned_developer_id`, `start_date`, `delivered_date`, `tat_days`, `drive_url`, `form_url`, `notes`

### DomainRenewal, ProjectStatusHistory
Supporting tables for domain alerts and status change audit.

---

## 🎨 Design System

### Colors (Tailwind CDN)
- **Primary:** Blue 600 (`#2563eb`)
- **Success:** Green 600 (`#10b981`)
- **Warning:** Amber 600 (`#f59e0b`)
- **Danger:** Red 600 (`#ef4444`)
- **Neutral:** Slate 100-900

### Typography
- System font stack via Tailwind defaults
- Headings use `font-bold`, body uses `font-medium` or default
- Small UI text: `text-xs` (12px) or `text-sm` (14px)

### Patterns
- **Cards:** `bg-white rounded-lg shadow p-5` or `p-6`
- **Buttons:** `bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium`
- **Forms:** `border border-slate-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none`
- **Status badges:** `text-xs font-medium px-2 py-1 rounded` with contextual bg color

### JavaScript Behavior
- **SweetAlert2** for destructive confirms via `data-confirm` attribute on forms
- **Toast notifications** for flash messages (bottom-right, auto-dismiss 3.5s)
- **Chart.js 4.4.0** for dashboard visualizations

---

## 🧪 Database Reset Procedure

When `models.py` changes (new column, new table), reset the DB:

**Mac:**
```bash
rm -rf instance
python3 seed.py
```

**Windows:**
```powershell
Remove-Item -Recurse -Force instance
python seed.py
```

⚠️ **This destroys all test data** including manually created leads/invoices/attendance. Only do this when the schema actually changed.

---

## 🚨 Common Errors & Fixes

### "ModuleNotFoundError: No module named 'flask'"
Your venv isn't active. Run:
- Mac: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

Then `pip install -r requirements.txt` if first time.

### "OperationalError: no such column: users.X"
Schema changed but DB wasn't reset. Delete `instance/` folder and re-run `seed.py`.

### "address already in use" on port 5001
Flask is already running in another terminal. Find and kill it:
- Mac: `lsof -ti:5001 | xargs kill -9`
- Windows: `Get-NetTCPConnection -LocalPort 5001 | Stop-Process -Id $_.OwningProcess -Force`

### "running scripts is disabled on this system" (Windows PowerShell)
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### "fatal: Authentication failed" on `git push`
GitHub requires a Personal Access Token (not password):
1. Go to https://github.com/settings/tokens
2. Generate new token (classic) → check `repo` scope → copy
3. Use token as password when Git prompts

### "fatal: refusing to merge unrelated histories"
Branch mismatch. Make sure you're on `expansion`:



### White screen on login
Template rendering error. Check Flask terminal for red traceback. Usually a Jinja syntax issue or missing block.

### "ValueError: Invalid format string" (Windows only)
Mac-only date format code (`%-d`) used in template. Replace with cross-platform pattern (see Cross-Platform Code Rules above).

---

## 📦 Dependencies (`requirements.txt`)



---

## 🚀 Deployment Notes (Future)

### Why Hostinger shared hosting won't work
Flask needs a Python runtime server. Hostinger's shared hosting only serves PHP/static files.

### Recommended free hosts
- **Render.com** — free tier, ~5-10 min setup, auto-deploy from GitHub
- **Railway.app** — free tier, similar workflow
- **PythonAnywhere** — free tier for Flask specifically

### Required changes before deploying
1. Move `SECRET_KEY` out of code into environment variable
2. Switch from SQLite → PostgreSQL (free on Render)
3. Add `gunicorn` to `requirements.txt` as production server
4. Add `Procfile` with: `web: gunicorn app:app`
5. Set debug=False in production

---

## 📝 Phase History

### Phase 1 (completed)
- Base attendance tracker (time-in/out, VL/SL marking, monthly calendar)
- Admin panel for employees and attendance editing with audit trail
- Rebranded from AFSI to Artchelo Design
- Sales module: Leads + Invoices + Clients CRUD
- Dashboard with 5 Chart.js visualizations

### Phase 2a (completed)
- Website Projects module (CRUD + filter + search)
- Project / DomainRenewal / ProjectStatusHistory tables
- 50 seeded sample projects
- 2 new dashboard charts (Projects by Tier, Developer Workload)

### Phase 2b (completed)
- Employee profile fields (job position, birthdate, salary, employment status)
- Soft-delete via employment_status (active/on_leave/resigned/terminated)
- Non-active users blocked from login
- `admin_edit_employee` full profile editor
- Team list filter + "Show all" toggle

### Phase 2c (completed)
- Middle initial field + "First M. Last" display format
- SweetAlert2 for confirm dialogs
- Toast notifications for flash messages
- Team page search bar (filter by first/last name)
- Self-service password change (`/account/change-password`)
- Cross-platform date formatting (Windows compatibility)

### Phase 2d (ideas for future)
- CSV importer for Projects with dry-run preview
- Status history timeline UI per project
- Domain renewal reminders (30/60/90 days)
- CSV export for attendance/projects
- Deploy to Render (requires migration to PostgreSQL)

---

## 🔗 Useful Links

- **Repo:** https://github.com/artchill/artchelo-design-hub
- **GitHub tokens:** https://github.com/settings/tokens
- **Python docs:** https://docs.python.org/3/
- **Flask docs:** https://flask.palletsprojects.com/
- **Tailwind CSS:** https://tailwindcss.com/docs
- **Chart.js:** https://www.chartjs.org/docs/latest/
- **SweetAlert2:** https://sweetalert2.github.io/

---

*Last updated: 2026-10-21 — Phase 2c complete, running on Mac + Windows*