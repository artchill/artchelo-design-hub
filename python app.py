[33mcommit c27ff7ece948a1cbb864c5d449be9329ab773b56[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mexpansion[m[33m, [m[1;31morigin/expansion[m[33m)[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Tue Oct 27 21:51:33 2026 +0800

    Promote admin edit + hide super-admin edit trail + View History + fix Cancel UX
    
    PERMISSIONS:
    - Admin can now Edit attendance records (previously super-admin only)
    - Add and Remove attendance remain super-admin only
    
    AUDIT PRIVACY:
    - Pencil icon hidden from admin viewers when super-admin was the editor
    - Super-admin viewers see all edit trails
    - Applied consistently across _calendar_table and employee_dashboard
    
    VIEW HISTORY:
    - 'History' link next to pencil icon
    - Opens SweetAlert2 modal with editor name, role, date, time
    - Same visibility rule as pencil icon
    - No new DB table — uses existing edited_at and edited_by_id fields
    - Added edited_by relationship on Attendance model
    
    UX FIX:
    - Cancel buttons on Edit/Add attendance pages now return to the same employee + same month viewed
    - Back to Attendance link preserves employee + month context
    - Fixes bug where Cancel redirected to first employee alphabetically

[33mcommit e79ddf03a1dca6291c705a4d04491a6b13d49708[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Tue Oct 27 19:01:52 2026 +0800

    Phase 3 complete: super-admin role, attendance export, backfill, remove, 404 page
    
    ROLES (super-admin / admin / employee):
    - Super-admin: full access, invisible to admins and attendance tracker
    - Admin: can mark VL/SL but cannot edit attendance (super-admin only)
    - Employee: unchanged
    - cheluarbuis migrated from admin to super-admin
    - Seeded aadmin test account for admin role testing
    
    ATTENDANCE:
    - Export: xlsx or csv dropdown next to View button (admin+ only)
      - Styled Excel with color-coded status, auto-column widths, frozen panes
      - CSV with UTF-8 BOM for Excel compatibility
      - Merges multiple sessions per day into one row
      - Includes summary totals at bottom
    - Backfill: super-admin can Add attendance for past days with no record
    - Remove: super-admin can delete accidental attendance records
    - Rejects: future dates, days with existing attendance/leave
    
    PRIVACY:
    - Super-admins hidden from Team list, search, attendance tracker
    - Admin visiting super-admin URL -> 404
    - Dashboard charts anonymize super-admin names
    - Super-admins still see each other on Team page
    
    UI:
    - Removed AFSI from attendance page title (Phase 1 cleanup)
    - 'No Work' label -> 'Weekend'
    - Super-admin purple badge on Team list and sidebar footer
    - Custom branded 404 page (works for both logged-in and public)
    
    Dependencies: openpyxl
    Migration: run migrate_super_admin.py once (idempotent)

[33mcommit 509a5251df72ee6602a8a285881f415e0725fa23[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Tue Oct 27 03:33:04 2026 +0800

    Add super-admin role + monthly attendance export
    
    PERMISSIONS SYSTEM:
    - Three roles: super-admin, admin, employee
    - Super-admin: full access to everything
    - Admin: all current admin powers EXCEPT editing attendance records (only mark VL/SL)
    - Admin cannot create super-admin users
    - Admin cannot change role of super-admin users
    - Super-admin inherits all admin permissions
    - cheluarbuis migrated from admin → super-admin
    - Seeded aadmin/admin123 as test admin
    - Backend enforces at both UI (hidden buttons) and route level (access denied)
    
    ATTENDANCE EXPORT:
    - New routes: /admin/employees/<id>/export/xlsx and /export/csv
    - XLSX uses openpyxl with styled headers, color-coded status
    - CSV uses UTF-8 BOM for Excel compatibility
    - Export dropdown button next to View on tracker page
    - Multiple sessions per day merged into single row
    
    UI:
    - 'No Work' status label → 'Weekend' (internal value stays 'no_work')
    - Removed 'AFSI' from attendance tracker page title (missed in Phase 1 rebrand)
    - Super-admin badge in sidebar footer + Team list
    
    Dependencies added: openpyxl
    Migration: run migrate_super_admin.py once per DB (idempotent)

[33mcommit 1d5906ca9370549b674f76b50610d2362fa1f5c3[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Thu Oct 22 03:59:39 2026 +0800

    Add employee profile fields: codename, email, gender, avatar
    
    New User fields:
    - codename (optional, max 30 chars)
    - email (required, unique, lowercased on save)
    - profile_pic (file upload, auto-resized to 400x400 with EXIF orientation fix)
    - gender (required, male/female/prefer_not_to_say)
    
    Profile pic storage:
    - Local disk: static/uploads/avatars/
    - Pillow verifies real file type (not just MIME claim)
    - Max 2MB, JPG/PNG/WEBP only
    - Old files deleted on replace or remove
    - Gitignored except .gitkeep to preserve folder structure
    
    UI changes:
    - Team list columns: ID | Full Name (with avatar) | Codename | Username | Email (mailto) | Job | Status | Actions
    - Add Employee form includes all new fields
    - Edit Employee shows avatar preview + remove checkbox
    - Sidebar footer uses avatar if uploaded, falls back to initials
    
    Technical:
    - Pillow 13.0.0 (compatible with Python 3.15)
    - DB reset required: email is a new required column

[33mcommit 1db9b9242a7b636d5d52e13223a51fb46a96738b[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Thu Oct 22 01:53:42 2026 +0800

    Add developer guide (DOCS.md)

[33mcommit d9c5ffafcbbeb57d059a38a6462ff6912a3aa5da[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Wed Oct 21 04:35:49 2026 +0800

    Fix cross-platform date formatting (%-d → %d with strip zero)

[33mcommit d1f449be45053000833eb5668cec3af40e230c5d[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Fri Oct 16 02:09:52 2026 +0800

    Add self-service password change for all users
    
    - New /account/change-password route (any logged-in user)
    - Requires current password verification before change
    - Enforces: min 6 chars, must differ from current, confirm must match
    - Sidebar footer link visible to both admins and employees

[33mcommit d65494fdd3a9c30bfdeff4cc06ead694808597fc[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Fri Oct 16 01:52:29 2026 +0800

    Phase 2c: middle initial, SweetAlert2, toasts, team search
    
    - Add mname field (max 2 chars) to User model with full_name + initials properties
    - Display 'First M. Last' format in sidebar footer and Team table
    - Replace browser confirm() with SweetAlert2 modal via data-confirm attribute
    - Replace flash messages with toast notifications (bottom-right, auto-dismiss)
    - Add search bar on Team page (filters by first/last name, case-insensitive)
    - Search persists via ?q=... URL param, works alongside show_all filter
    - Seed Chilli (L.), John (A.), Alice (M.) with middle initials

[33mcommit cd984152b665c4748ced079e52edb6edf099282c[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Fri Oct 16 00:28:08 2026 +0800

    Save work before Phase 2b

[33mcommit 3deb74eb82ced8ad8ac98788c95bd193c1c92828[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Thu Oct 15 21:08:39 2026 +0800

    Fix: base.html block mismatch broke logged-out pages (white screen)

[33mcommit 4b4dfd0a8dbcaf0e8a2f19d94a2a714453b916cb[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Thu Oct 15 12:44:52 2026 +0800

    Phase 2a: Website Projects module
    
    - New models: Project, DomainRenewal, ProjectStatusHistory
    - Projects CRUD with filter/search (status, tier, developer)
    - 50 seeded sample projects
    - New dashboard KPIs: Projects Total, Ongoing, Delivered, Avg TAT
    - New dashboard charts: Projects by Tier + Developer Workload
    - Rename admin user to cheluarbuis
    - Activate 'Website Projects' sidebar link

[33mcommit c9815c2a93b49f7db334795c08b9053db5eb0025[m
Author: artchill <cheluarbuis@gmail.com>
Date:   Thu Oct 15 02:08:47 2026 +0800

    Phase 1 complete: sales module + Artchelo rebrand + dashboard with Chart.js

[33mcommit 9df2f7eab8e97f94c5f78e76f01c4e9e7cfcaeb1[m
Author: Chelu Arbuis <richellou@Richellous-MacBook-Pro.local>
Date:   Fri May 15 17:14:42 2026 +0800

    Your description of what changed

[33mcommit 2269d3c7a74209b6f666a20939ed55ffb5caca68[m
Author: Chelu Arbuis <richellou@Richellous-MacBook-Pro.local>
Date:   Tue May 5 03:48:31 2026 +0800

    Add admin features: create users and edit attendance with audit trail
    
    - Fix pbkdf2 password hashing for Python 3.9 compatibility
    - Improve datetime display: separate date and time, 12-hour format
    - New: Admin can create users (employees and admins) with validation
    - New: Admin can edit attendance records with auto-recalculated hours
    - New: Audit trail tracks who edited each record and when
    - Change default port to 5001 to avoid macOS AirPlay conflict

[33mcommit 8ecd9f7b7351b52d42e9c535d04e20e618bfcd16[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:13:34 2026 +0800

    Delete CNAME

[33mcommit 566e732b27d1a0badb9678a971ea2b750d49beb9[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:11:39 2026 +0800

    Create CNAME

[33mcommit 29596a2d6c14110a1d0cc71a75adab772e335f31[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:02:21 2026 +0800

    Add files via upload

[33mcommit e73908434de01698b0d2981d80583f0fbb565cdc[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:01:53 2026 +0800

    Delete login.html

[33mcommit 5defe8a9e5e0ef1083c4633b5caf03673781c6c5[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:01:41 2026 +0800

    Delete base.html

[33mcommit fcb1c8a12841e38a59adf6da5b57b731afe02c1d[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:01:20 2026 +0800

    Delete employee_dashboard.html

[33mcommit e147796787efe4bd55d5c024c2bbc9cd3df14afd[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:01:09 2026 +0800

    Delete admin_employees.html

[33mcommit 1fd02d93461193515e1638222a9975658c5eb708[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:00:58 2026 +0800

    Delete admin_dashboard.html

[33mcommit 7568d7b8afa1f4b7672fc4cf78ee9bcfa8673bb1[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 02:00:38 2026 +0800

    Delete templates

[33mcommit ddf3b380a143ffb77ba93b217b23f839183791f1[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 01:55:39 2026 +0800

    Create templates

[33mcommit 08d7ae223633624048e8329d704c5ed7c4fc2f90[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 01:53:53 2026 +0800

    Add files via upload

[33mcommit 8368566420e173f4e92ba8c661f9f6c7a2135ee1[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 01:53:23 2026 +0800

    Delete templates

[33mcommit 646d014b48beba01631e8599a1c0c653240f0dd5[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 01:51:49 2026 +0800

    Create templates

[33mcommit 6107ebb6eb1e3cbd60ed9fbf41d38263859ef0bd[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 01:51:15 2026 +0800

    Add files via upload

[33mcommit 69ec251eea32401a65fdfdc6f0d58c64eff4ca69[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 01:48:40 2026 +0800

    Add README for Attendance Tracker System
    
    Added detailed documentation for the Attendance Tracker System, including features, tech stack, project structure, installation instructions, default credentials, and future roadmap.

[33mcommit b383973fba69f1937223e78e700d519e67f59c69[m
Author: chelu arbuis <40821850+artchill@users.noreply.github.com>
Date:   Tue May 5 01:47:55 2026 +0800

    Add .gitignore for Python and Flask projects
