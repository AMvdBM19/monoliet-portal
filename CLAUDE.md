# monoliet-portal — Claude Code Project

## What this is

The Monoliet Client Portal: a Django 5.0 ERP/CRM for managing automation clients.
Lives at portal.monoliet.cloud. Serves two user types: admin (Andres) and
client-facing portal users. This is the primary business command center —
invoicing, workflow monitoring, support tickets, and (in progress) AI-powered
client utilities.

---

## Environment

**VPS path:** `/opt/docker/monoliet-portal/`
**Local path:** `C:\Users\Andres\Desktop\Monoliet Portal Repository\monoliet-portal`
**Git remote:** `github.com/AMvdBM19/monoliet-portal` (private)
**Live URL:** `https://portal.monoliet.cloud`
**Admin URL:** `https://portal.monoliet.cloud/admin`

**Docker containers:**

* `monoliet-django` — Gunicorn on port 8000
* `monoliet-postgres` — PostgreSQL 15

**Docker network:** `web` (external, shared with Nginx Proxy Manager and n8n)
**Static files:** served by WhiteNoise via `/app/staticfiles/`
**Claude Code runs as root from:** `/opt/docker/monoliet-portal/`

---

## Stack

| Layer        | Technology                     |
| ------------ | ------------------------------ |
| Framework    | Django 5.0.1                   |
| API          | Django REST Framework 3.14.0   |
| Database     | PostgreSQL 15                  |
| Server       | Gunicorn 3 workers             |
| Static files | WhiteNoise 6.6.0               |
| Encryption   | cryptography 42.0.0 (Fernet)   |
| HTTP client  | httpx 0.25.2 (MCP integration) |
| Auth         | DRF Token + Django session     |

---

## Repository structure

```
monoliet-portal/
├── portal/                  # Django project config
│   ├── settings.py
│   ├── urls.py              # Root URLs — MCP/execution routes BEFORE admin/
│   └── wsgi.py
├── clients/                 # Main app — all business logic lives here
│   ├── models.py            # 9 models (Client, Workflow, Execution, Invoice,
│   │                        #   SupportTicket, APICredential, ClientProfile,
│   │                        #   PortalSettings, NotionIntakeSession)
│   ├── views.py             # DRF ViewSets — API endpoints
│   ├── web_views.py         # Django template views — client portal
│   ├── admin_views.py       # Custom admin dashboard
│   ├── execution_admin_views.py
│   ├── mcp_admin_views.py
│   ├── execution_sync.py    # n8n execution sync service
│   ├── serializers.py
│   ├── permissions.py       # IsAdminUser, IsClientOwner, IsClientUser, etc.
│   ├── signals.py           # Email triggers on save events
│   ├── forms.py
│   ├── utils.py             # Encryption, invoice numbers, N8NAPIClient
│   ├── urls.py              # API URL router
│   ├── web_urls.py          # Client portal URL patterns (app_name='portal')
│   ├── static/css/
│   │   ├── style.css        # Single @import — DO NOT add rules here
│   │   └── monoliet-design-system.css  # Single source of truth for all styling
│   ├── templates/
│   │   ├── admin/           # Django admin overrides
│   │   │   ├── base_site.html
│   │   │   ├── index.html
│   │   │   ├── mcp/
│   │   │   └── executions/
│   │   └── clients/         # Client portal templates
│   │       ├── base.html    # Sidebar layout — extends all client pages
│   │       ├── login.html   # Standalone — does NOT extend base.html
│   │       └── *.html
│   └── management/commands/ # sync_n8n_executions, send_invoice_reminders,
│                            #   check_workflow_health, create_sample_data,
│                            #   sync_executions
├── docs/
│   ├── MCP_INTEGRATION.md
│   └── MCP_DEPLOYMENT_GUIDE.md
├── CLAUDE.md                # This file
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Design system — MANDATORY reading before touching any template or CSS

All styling is in `clients/static/css/monoliet-design-system.css`.
`style.css` is a single `@import` — never add rules to it.

**Design tokens (use CSS variables, never hardcode hex values):**

```css
--bg-primary: #0B0D10
--bg-secondary: #0D0F12
--text-primary: #FFFFFF
--text-body: #DBDBDB
--text-muted: #9B9B9B
--text-dark: #1E1F2B
--accent-green: #22C55E
--accent-warning: #FBBF24
--accent-error: #EF4444
--accent-info: #3B82F6
--border: rgba(155, 155, 155, 0.2)
--glass-bg: rgba(0, 0, 0, 0.5)
--transition: 0.3s ease
--sidebar-width: 240px
--header-height: 64px
```

**Fonts:** Space Grotesk (headings/UI) · Space Mono (labels/mono) · Inter (body)
**Border radius:** 0px everywhere except 4px for cards (`--radius-card: 4px`)
**No Tailwind** — it was removed in Phase 1. Do not add Tailwind CDN or classes.

**Component classes to use:**

* Cards: `.glass-card`, `.glass-card--accent`, `.glass-card--flat`, `.stat-card`
* Buttons: `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-dark`, `.btn-danger`, `.btn-sm`, `.btn-lg`
* Badges: `.badge`, `.badge--green`, `.badge--yellow`, `.badge--red`, `.badge--blue`, `.badge--gray`
* Tables: `.data-table`, `.data-table--fixed`
* Forms: `.form-group`, `.form-label`, `.form-input`, `.form-select`, `.form-textarea`, `.form-help`, `.form-error`
* Alerts: `.alert`, `.alert--success`, `.alert--warning`, `.alert--error`, `.alert--info`
* Layout: `.portal-sidebar`, `.portal-main`, `.portal-header`, `.portal-content`, `.portal-content__inner`
* Page header: `.page-header`, `.page-header__eyebrow`, `.page-header__title`, `.page-header__sub`
* Grid: `.grid-2`, `.grid-3`, `.grid-4`
* Admin: `.admin-page`, `.admin-tabs`, `.admin-tab`, `.admin-tab--active`, `.chart-card`
* Utilities: `.flex-between`, `.flex-center`, `.gap-sm/md/lg`, `.text-primary/muted/green/red/yellow`, `.mono`, `.label`

---

## Template architecture

**Two separate template trees — keep them separate:**

| Tree          | Base template                              | Extends           | Used for                                            |
| ------------- | ------------------------------------------ | ----------------- | --------------------------------------------------- |
| Client portal | `clients/templates/clients/base.html`    | All client pages  | Dashboard, workflows, invoices, support, executions |
| Admin         | `clients/templates/admin/base_site.html` | Django admin base | All admin pages                                     |
| Standalone    | none                                       | —                | `login.html`only                                  |

`base.html` (client portal) implements the sidebar layout:
`portal-sidebar` → `portal-main` → `portal-header` → `portal-content` → `portal-content__inner`

Active sidebar link detection uses `request.path` string matching.
Logout uses POST form with `{% csrf_token %}` — never change this to GET.

**Required blocks in client templates:**

* `{% block title %}` — browser tab title
* `{% block page_title %}` — shown in portal header
* `{% block content %}` — page body
* `{% block extra_css %}` / `{% block extra_js %}` — optional additions

**Required blocks in admin templates:**

* `{% block extrastyle %}` — loads design system CSS
* `{% block extrahead %}` — loads Google Fonts
* Preserve `{% block branding %}`, `{% block userlinks %}` — Django admin requires these

---

## URL routing rules

`portal/urls.py` has a strict ordering requirement:

1. MCP routes (`/admin/mcp/...`) — MUST come first
2. Execution routes (`/admin/executions/...`) — MUST come before Django admin
3. Django admin (`/admin/`) — MUST come after custom admin routes
4. API routes (`/api/...`)
5. Client portal routes (catch-all `''`)

**Do not reorder these.** Custom routes placed after `path('admin/', ...)` will be shadowed by Django admin.

**Client portal URL names** (app_name = 'portal'):
`portal:dashboard`, `portal:workflows`, `portal:executions`, `portal:execution-detail`,
`portal:execution-stats-api`, `portal:invoices`, `portal:support`, `portal:create-ticket`,
`portal:login`, `portal:logout`

---

## Hard constraints — NEVER violate

1. **Never touch `portal/urls.py` route ordering** without re-reading the ordering rules above.
2. **Never add Tailwind CDN** or Tailwind utility classes to any template.
3. **Never hardcode hex color values** in templates or CSS — use CSS variables.
4. **Never add inline `<style>` blocks** to templates — all styles go in the design system.
5. **Never modify migration files** that have already been applied on the VPS.
6. **Never write files directly to the VPS.** Always: edit locally → commit → push → pull on VPS → restart container.
7. **`style.css` is a single @import.** Do not add any CSS rules to it.
8. **`forms.py` widget classes** must use `.form-input` / `.form-select` — not Tailwind classes.
9. **`{% csrf_token %}` must be present** in every POST form. Never remove it.
10. **Chart.js initialization JS blocks** in admin templates must not be modified — they depend on Django template context variables injected by `admin_views.py`.

---

## Deployment workflow

```bash
# On VPS — standard deploy after git push from local
cd /opt/docker/monoliet-portal
git pull origin main
docker-compose exec django python manage.py collectstatic --noinput
docker-compose restart django
docker-compose ps   # confirm healthy
```

**After model changes (migrations):**

```bash
docker-compose exec django python manage.py makemigrations
docker-compose exec django python manage.py migrate
docker-compose restart django
```

**Static files must be collected** after any change to CSS or JS files.
WhiteNoise's `CompressedManifestStaticFilesStorage` will serve stale files
until `collectstatic` is run.

---

## Authentication & permissions

Two user types — both use Django auth:

| Type           | Flag               | Access                                  |
| -------------- | ------------------ | --------------------------------------- |
| Admin (Andres) | `is_staff=True`  | Full portal + Django admin              |
| Client user    | `is_staff=False` | Own client data only, via ClientProfile |

`ClientProfile` links a Django `User` → `Client`. Client users who have no
linked profile see `clients/no_client.html`.

Permission classes in `clients/permissions.py`:
`IsAdminUser`, `IsClientOwner`, `IsClientUser`, `CanCreateSupportTicket`,
`IsAdminOrReadOnly`, `ReadOnly`

API uses DRF Token auth. Client portal uses Django session auth.

---

## Models — quick reference

```
Client          — company, billing, plan_tier, status (active/paused/churned)
Workflow        — linked to Client, n8n_workflow_id, status (active/paused/error)
Execution       — daily stats per Workflow (total/success/error counts)
Invoice         — billing records, auto-generated invoice numbers (INV-YYYY-XXX)
SupportTicket   — client support, priority (low/medium/high), status (open/in_progress/resolved)
APICredential   — Fernet-encrypted third-party credentials
ClientProfile   — OneToOne(User) → ForeignKey(Client)
PortalSettings  — singleton config (n8n API, MCP server settings)
NotionIntakeSession — Telegram bot session state for n8n intake workflow
```

All business models use UUID primary keys. All have `created_at` / `updated_at`.

**Signals in `signals.py`** send emails automatically on:

* New SupportTicket → email to client + admin
* SupportTicket resolved → email to client
* New Invoice → email to client
* Workflow enters error state → email to admin
* Invoice pre-save → auto-generate invoice number

---

## n8n integration

`N8NAPIClient` in `clients/utils.py` handles all n8n API calls.
Config: `settings.N8N_URL`, `settings.N8N_API_KEY` (from `.env`).

**Execution sync** runs via management command or `ExecutionSyncService`:

```bash
docker-compose exec django python manage.py sync_executions --limit 100
```

**Do not modify** the `NotionIntakeSession` model or the `intake_session_view`
endpoint in `views.py` — this is owned by an active n8n workflow.

---

## MCP server integration

The portal has an admin UI at `/admin/mcp/` for managing the MCP server.
Config lives in `PortalSettings` (singleton model). The MCP client is in
`clients/mcp_client.py` — async httpx. The admin views use `run_async()`
helper to bridge sync Django views with async client calls.

MCP routes are defined in `portal/urls.py` and MUST remain above the Django
admin route.

---

## Development phases (current roadmap)

| Phase | Status      | Description                                                                 |
| ----- | ----------- | --------------------------------------------------------------------------- |
| 1     | ✅ Complete | Design system foundation + template cleanup                                 |
| 2     | Next        | New data models (ClientEvent, Contact, AIConversation) + migrations         |
| 3     | Planned     | Client utilities — tier-gated features (contact CRM, report builder)       |
| 4     | Planned     | AI assistant — admin + client-facing, context-aware Claude API integration |
| 5     | Planned     | Admin utilities — client health score, onboarding checklist, revenue panel |

**Phase 2 note:** `plan_tier` on the `Client` model is currently a free-text
`CharField`. Before adding tier-gated features, decide whether to convert it
to choices or add a separate `Plan` model. Do not implement tier-gating
until this decision is made and documented.

---

## Pre-flight checklist for every Claude Code session

Before writing any code, run:

```bash
cat portal/settings.py | grep -E "STATIC|INSTALLED_APPS|TEMPLATES" | head -20
cat clients/static/css/style.css
ls clients/templates/clients/
ls clients/templates/admin/
docker-compose ps
```

Confirm:

* `django.contrib.staticfiles` is in `INSTALLED_APPS`
* `style.css` contains only the `@import` line
* All expected templates exist
* Both containers are running/healthy

---

## Environment variables (see `.env`, never commit values)

```
SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER,
EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL
N8N_URL, N8N_API_KEY
ENCRYPTION_KEY        ← CRITICAL: never change after data is encrypted
INTAKE_TOKEN          ← used by n8n Telegram bot endpoint
```
