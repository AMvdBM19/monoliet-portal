# Monoliet Client Portal - Quick Setup Guide

This guide will walk you through setting up the Monoliet Client Portal from scratch.

## Step-by-Step Setup

### 1. Prepare Your Environment

```bash
# Ensure Docker is installed and running
docker --version
docker-compose --version

# Ensure the 'web' network exists (used by Nginx Proxy Manager)
docker network create web || echo "Network already exists"
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Generate an encryption key for API credentials
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env and update these critical values:
# - SECRET_KEY (generate a strong random key)
# - ENCRYPTION_KEY (use the key generated above)
# - DB_PASSWORD (choose a strong password)
# - EMAIL_HOST_USER (your email)
# - EMAIL_HOST_PASSWORD (your email app password)
# - N8N_API_KEY (from your n8n instance)
```

### 3. Build and Start Containers

```bash
# Build the Docker images
docker-compose build

# Start the services
docker-compose up -d

# Check that services are running
docker-compose ps

# You should see:
# - monoliet-postgres (healthy)
# - monoliet-django (running)
```

### 4. Initialize the Database

```bash
# Create database tables
docker-compose exec django python manage.py makemigrations
docker-compose exec django python manage.py migrate

# Expected output: Several migrations applied successfully
```

### 5. Create Admin User

```bash
# Create superuser account
docker-compose exec django python manage.py createsuperuser

# You'll be prompted to enter:
# - Username (e.g., admin)
# - Email (e.g., admin@monoliet.cloud)
# - Password (choose a strong password)
```

### 6. Collect Static Files

```bash
# Gather all static files for serving
docker-compose exec django python manage.py collectstatic --noinput
```

### 7. Create Sample Data (Optional)

```bash
# Generate test data for development
docker-compose exec django python manage.py create_sample_data

# This creates:
# - 3 sample clients
# - 6 sample workflows
# - 30 days of execution data
# - Sample invoices and support tickets
# - 3 test client users
```

### 8. Configure Nginx Proxy Manager

Access your Nginx Proxy Manager and add a new Proxy Host:

**Settings:**
- **Domain Names**: `portal.monoliet.cloud`
- **Scheme**: `http`
- **Forward Hostname/IP**: `monoliet-django`
- **Forward Port**: `8000`
- **Cache Assets**: Yes (optional)
- **Block Common Exploits**: Yes
- **Websockets Support**: No

**SSL:**
- **SSL Certificate**: Request a new Let's Encrypt certificate
- **Force SSL**: Yes
- **HTTP/2 Support**: Yes
- **HSTS Enabled**: Yes

### 9. Verify Installation

**Test Admin Panel:**
```bash
# Access: https://portal.monoliet.cloud/admin
# Login with your superuser credentials
```

**Test Client Portal:**
```bash
# Access: https://portal.monoliet.cloud/
# If you created sample data, login with:
# Username: john_acme
# Password: demo1234
```

**Test API:**
```bash
# Get authentication token
curl -X POST https://portal.monoliet.cloud/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# Use the returned token for API calls
curl https://portal.monoliet.cloud/api/clients/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### 10. Set Up Cron Jobs (Production)

```bash
# Edit crontab
crontab -e

# Add these lines:
0 2 * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py sync_n8n_executions
0 9 * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py send_invoice_reminders
0 * * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py check_workflow_health
```

## Common Tasks

### Adding a New Client

**Via Admin Panel:**
1. Go to https://portal.monoliet.cloud/admin
2. Click "Clients" → "Add Client"
3. Fill in company details, plan tier, and billing info
4. Save

**Via API:**
```bash
curl -X POST https://portal.monoliet.cloud/api/clients/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "New Client Co",
    "contact_name": "Jane Doe",
    "email": "jane@newclient.com",
    "plan_tier": "Business Process",
    "setup_fee": "500.00",
    "monthly_fee": "297.00",
    "billing_cycle": "monthly",
    "next_billing_date": "2024-02-01"
  }'
```

### Creating a Client User Account

1. In admin panel, go to "Users" → "Add User"
2. Create username and password
3. Save, then edit the user
4. Go to "Client Profiles" → "Add Client Profile"
5. Link the user to their client
6. User can now login at https://portal.monoliet.cloud/

### Adding a Workflow

1. Create workflow in n8n
2. Note the workflow ID from n8n URL
3. In admin panel, "Workflows" → "Add Workflow"
4. Select client, enter workflow name and n8n workflow ID
5. Save

### Generating an Invoice

**Manual:**
1. Admin panel → "Invoices" → "Add Invoice"
2. Select client, enter amount and due date
3. Invoice number auto-generates
4. Email automatically sent to client

**Programmatic:**
```python
# In Django shell
from clients.models import Invoice, Client
from datetime import date, timedelta
from decimal import Decimal

client = Client.objects.get(company_name="Acme E-commerce")
invoice = Invoice.objects.create(
    client=client,
    amount=client.monthly_fee,
    type='monthly',
    status='pending',
    due_date=date.today() + timedelta(days=30)
)
# invoice_number auto-generates
# Email auto-sends via signal
```

## Troubleshooting

### Container Issues

```bash
# View logs
docker-compose logs django
docker-compose logs postgres

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose down
docker-compose build
docker-compose up -d
```

### Database Issues

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U monoliet -d monoliet_clients

# Reset database (WARNING: Deletes all data!)
docker-compose down -v
docker-compose up -d
docker-compose exec django python manage.py migrate
```

### Email Not Sending

Check `.env` settings:
- `EMAIL_HOST_USER` = your Gmail address
- `EMAIL_HOST_PASSWORD` = App Password (not regular password)
- For Gmail: Enable 2FA, then create App Password at https://myaccount.google.com/apppasswords

Test email:
```python
# Django shell
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'Test Email',
    'This is a test.',
    settings.DEFAULT_FROM_EMAIL,
    ['test@example.com'],
    fail_silently=False,
)
```

### Static Files Not Loading

```bash
# Recollect static files
docker-compose exec django python manage.py collectstatic --noinput --clear

# Check STATIC_ROOT
docker-compose exec django ls -la /app/staticfiles/
```

## Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=False` in `.env`
- [ ] Update `ALLOWED_HOSTS` with your domain
- [ ] Generate strong `SECRET_KEY`
- [ ] Use strong database password
- [ ] Configure real email credentials
- [ ] Set up n8n API key
- [ ] Configure SSL in Nginx Proxy Manager
- [ ] Set up database backups
- [ ] Configure cron jobs
- [ ] Test all email notifications
- [ ] Test API endpoints
- [ ] Test client portal login
- [ ] Monitor logs for errors

## Support

For issues or questions:
- Email: info@monoliet.cloud
- Check logs: `docker-compose logs -f`
- Django shell: `docker-compose exec django python manage.py shell`

## Next Steps

1. Customize email templates in `clients/signals.py`
2. Add your logo to templates
3. Configure Stripe for payment processing
4. Set up backup automation
5. Configure monitoring and alerting
6. Add SSL certificate auto-renewal
