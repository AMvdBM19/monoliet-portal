# Monoliet Client Portal - Quick Reference

## Common Commands

### Docker Operations

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f
docker-compose logs -f django
docker-compose logs -f postgres

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
```

### Django Management

```bash
# Make migrations
docker-compose exec django python manage.py makemigrations

# Apply migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Collect static files
docker-compose exec django python manage.py collectstatic --noinput

# Django shell
docker-compose exec django python manage.py shell

# Create sample data
docker-compose exec django python manage.py create_sample_data
```

### Database Operations

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U monoliet -d monoliet_clients

# Backup database
docker-compose exec postgres pg_dump -U monoliet monoliet_clients > backup.sql

# Restore database
docker-compose exec -T postgres psql -U monoliet -d monoliet_clients < backup.sql

# Reset database (WARNING: Deletes all data!)
docker-compose down -v
docker-compose up -d
docker-compose exec django python manage.py migrate
```

### Automation Commands

```bash
# Sync n8n executions
docker-compose exec django python manage.py sync_n8n_executions --days=7

# Send invoice reminders
docker-compose exec django python manage.py send_invoice_reminders

# Check workflow health
docker-compose exec django python manage.py check_workflow_health --threshold=80
```

### API Testing

```bash
# Get auth token
curl -X POST https://portal.monoliet.cloud/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# List clients
curl https://portal.monoliet.cloud/api/clients/ \
  -H "Authorization: Token YOUR_TOKEN"

# Get current user's client
curl https://portal.monoliet.cloud/api/clients/me/ \
  -H "Authorization: Token YOUR_TOKEN"

# List workflows
curl https://portal.monoliet.cloud/api/workflows/ \
  -H "Authorization: Token YOUR_TOKEN"

# Get execution stats (last 30 days)
curl https://portal.monoliet.cloud/api/executions/stats/?days=30 \
  -H "Authorization: Token YOUR_TOKEN"

# Create support ticket
curl -X POST https://portal.monoliet.cloud/api/support-tickets/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test ticket",
    "description": "This is a test",
    "priority": "medium"
  }'
```

## Access URLs

- **Admin Panel**: https://portal.monoliet.cloud/admin
- **Client Portal**: https://portal.monoliet.cloud/
- **API Root**: https://portal.monoliet.cloud/api/
- **API Documentation**: https://portal.monoliet.cloud/api/ (browsable API)

## Default Credentials (After Sample Data Creation)

**Admin Account:**
- Created via `createsuperuser` command
- Username: (your choice)
- Password: (your choice)

**Test Client Users:**
- Username: `john_acme` | Password: `demo1234`
- Username: `sarah_digital` | Password: `demo1234`
- Username: `mike_tech` | Password: `demo1234`

## Environment Variables (.env)

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,portal.monoliet.cloud

# Database
DB_NAME=monoliet_clients
DB_USER=monoliet
DB_PASSWORD=your-db-password
DB_HOST=postgres
DB_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=info@monoliet.cloud
EMAIL_HOST_PASSWORD=your-app-password

# n8n
N8N_URL=https://n8n.monoliet.cloud
N8N_API_KEY=your-n8n-api-key

# Security
ENCRYPTION_KEY=your-fernet-encryption-key
```

## File Locations

**Configuration:**
- Settings: `portal/settings.py`
- Environment: `.env`
- Docker: `docker-compose.yml`

**Models:**
- All models: `clients/models.py`

**API:**
- Views: `clients/views.py`
- Serializers: `clients/serializers.py`
- URLs: `clients/urls.py`
- Permissions: `clients/permissions.py`

**Web Portal:**
- Views: `clients/web_views.py`
- Templates: `clients/templates/clients/`
- Forms: `clients/forms.py`

**Utilities:**
- Utils: `clients/utils.py`
- Signals: `clients/signals.py`
- Admin: `clients/admin.py`

**Management Commands:**
- Location: `clients/management/commands/`
- Sync n8n: `sync_n8n_executions.py`
- Reminders: `send_invoice_reminders.py`
- Health check: `check_workflow_health.py`
- Sample data: `create_sample_data.py`

## Troubleshooting

**Container won't start:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Database connection error:**
```bash
docker-compose restart postgres
docker-compose logs postgres
```

**Static files not loading:**
```bash
docker-compose exec django python manage.py collectstatic --noinput --clear
```

**Email not sending:**
- Check Gmail App Password (not regular password)
- Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env
- Test in Django shell:
  ```python
  from django.core.mail import send_mail
  send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
  ```

**Permission denied errors:**
```bash
sudo chown -R $USER:$USER .
```

## Cron Job Setup

```bash
# Edit crontab
crontab -e

# Add these lines (adjust path as needed)
0 2 * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py sync_n8n_executions
0 9 * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py send_invoice_reminders
0 * * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py check_workflow_health
```

## Model Relationships

```
Client
├── Workflows (one-to-many)
├── APICredentials (one-to-many)
├── Executions (one-to-many)
├── Invoices (one-to-many)
├── SupportTickets (one-to-many)
└── Users (via ClientProfile, one-to-many)

Workflow
├── Client (foreign key)
└── Executions (one-to-many)

Execution
├── Client (foreign key)
└── Workflow (foreign key)
```

## Status Values

**Client:**
- `active` - Currently using service
- `paused` - Temporarily suspended
- `churned` - No longer a client

**Workflow:**
- `active` - Running normally
- `paused` - Temporarily disabled
- `error` - Has errors

**Invoice:**
- `pending` - Not yet paid
- `paid` - Payment received
- `overdue` - Past due date

**Support Ticket:**
- `open` - New ticket
- `in_progress` - Being worked on
- `resolved` - Completed

## Quick Django Shell Snippets

```python
# Access Django shell
docker-compose exec django python manage.py shell

# Get all clients
from clients.models import Client
clients = Client.objects.all()

# Get a specific client
client = Client.objects.get(company_name="Acme E-commerce")

# Get client workflows
workflows = client.workflows.all()

# Get execution stats
from django.db.models import Sum
stats = client.executions.aggregate(
    total=Sum('total_count'),
    success=Sum('success_count')
)

# Create an invoice
from clients.models import Invoice
from datetime import date, timedelta
invoice = Invoice.objects.create(
    client=client,
    amount=client.monthly_fee,
    type='monthly',
    due_date=date.today() + timedelta(days=30)
)

# Get overdue invoices
from clients.utils import get_overdue_invoices
overdue = get_overdue_invoices()
```

## Production Checklist

Before going live:
- [ ] `DEBUG=False` in .env
- [ ] Strong `SECRET_KEY` generated
- [ ] Strong database password
- [ ] SSL certificate configured
- [ ] Email credentials configured
- [ ] n8n API key configured
- [ ] Cron jobs set up
- [ ] Database backup configured
- [ ] Tested all features
- [ ] Admin user created

## Support

- Email: info@monoliet.cloud
- Documentation: README.md, SETUP_GUIDE.md
- Logs: `docker-compose logs -f`
