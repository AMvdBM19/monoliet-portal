# Monoliet Client Portal

A comprehensive Django-based client management portal for Monoliet.cloud - a service that provides n8n automation workflows to clients.

## Features

### Admin Features
- Full client management with financial tracking
- Workflow monitoring with n8n integration
- Invoice generation and tracking
- Support ticket management
- Detailed execution statistics and analytics
- Email notifications for important events

### Client Features
- Personal dashboard with workflow overview
- Real-time execution statistics
- Invoice viewing and payment tracking
- Support ticket creation and tracking
- Secure, role-based access control

## Tech Stack

- **Backend**: Django 5.0 (Python)
- **Database**: PostgreSQL 15
- **API**: Django REST Framework
- **Container**: Docker & Docker Compose
- **Proxy**: Nginx Proxy Manager (pre-configured)
- **Styling**: Tailwind CSS (via CDN)
- **Integration**: n8n REST API

## Project Structure

```
monoliet-portal/
├── portal/                 # Django project settings
│   ├── settings.py        # Configuration
│   ├── urls.py            # Main URL routing
│   └── wsgi.py            # WSGI application
├── clients/               # Main application
│   ├── models.py         # Database models
│   ├── views.py          # API views
│   ├── web_views.py      # Web interface views
│   ├── serializers.py    # DRF serializers
│   ├── permissions.py    # Custom permissions
│   ├── admin.py          # Admin configuration
│   ├── signals.py        # Email notifications
│   ├── forms.py          # Django forms
│   ├── utils.py          # Utility functions
│   ├── templates/        # HTML templates
│   └── management/       # Management commands
├── docker-compose.yml    # Docker services
├── Dockerfile            # Django container
└── requirements.txt      # Python dependencies
```

## Database Schema

### Models
1. **Client** - Company information, billing details, plan tier
2. **Workflow** - n8n workflow tracking with status
3. **APICredential** - Encrypted third-party API credentials
4. **Execution** - Daily execution statistics per workflow
5. **Invoice** - Billing and payment tracking
6. **SupportTicket** - Customer support management
7. **ClientProfile** - Links Django users to clients

## Installation & Setup

### Prerequisites
- Docker and Docker Compose
- Existing Docker network named "web"
- Domain configured: portal.monoliet.cloud

### 1. Clone and Configure

```bash
# Clone the repository
cd monoliet-portal

# Create environment file
cp .env.example .env

# Edit .env with your actual values
nano .env
```

### 2. Generate Encryption Key

```bash
# Generate a Fernet encryption key for API credentials
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add the output to ENCRYPTION_KEY in .env
```

### 3. Build and Start Services

```bash
# Build and start containers
docker-compose up -d

# Wait for PostgreSQL to be ready
docker-compose logs -f postgres
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec django python manage.py makemigrations
docker-compose exec django python manage.py migrate

# Create superuser (admin account)
docker-compose exec django python manage.py createsuperuser

# Collect static files
docker-compose exec django python manage.py collectstatic --noinput
```

### 5. Create Test Data (Optional)

```bash
# Generate sample data for testing
docker-compose exec django python manage.py create_sample_data
```

### 6. Configure Nginx Proxy Manager

Add a proxy host in Nginx Proxy Manager:
- **Domain**: portal.monoliet.cloud
- **Forward Hostname/IP**: monoliet-django
- **Forward Port**: 8000
- **Enable SSL**: Yes (Let's Encrypt)

## API Endpoints

### Authentication
- `POST /api/auth/token/` - Get authentication token
- `POST /api/auth/logout/` - Logout and revoke token

### Clients
- `GET /api/clients/` - List all clients (admin only)
- `GET /api/clients/:id/` - Get client details
- `GET /api/clients/me/` - Get current user's client
- `POST /api/clients/` - Create client (admin only)
- `PUT /api/clients/:id/` - Update client

### Workflows
- `GET /api/workflows/` - List workflows
- `GET /api/workflows/:id/` - Get workflow details
- `POST /api/workflows/` - Create workflow (admin only)
- `PATCH /api/workflows/:id/activate/` - Activate/pause workflow

### Executions
- `GET /api/executions/` - List executions
- `GET /api/executions/stats/` - Get execution statistics
- `POST /api/executions/` - Create execution record

### Invoices
- `GET /api/invoices/` - List invoices
- `GET /api/invoices/:id/` - Get invoice details
- `GET /api/invoices/:id/download/` - Download invoice PDF

### Support Tickets
- `GET /api/support-tickets/` - List tickets
- `POST /api/support-tickets/` - Create ticket
- `PATCH /api/support-tickets/:id/` - Update ticket status

## Management Commands

Run these commands via cron for automation:

### Sync n8n Executions (Daily)
```bash
# Sync execution data from n8n
docker-compose exec django python manage.py sync_n8n_executions --days=7
```

### Send Invoice Reminders (Daily)
```bash
# Send payment reminders for upcoming/overdue invoices
docker-compose exec django python manage.py send_invoice_reminders
```

### Check Workflow Health (Hourly)
```bash
# Monitor workflows and alert on errors
docker-compose exec django python manage.py check_workflow_health --threshold=80
```

### Example Cron Configuration

```cron
# Sync executions daily at 2 AM
0 2 * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py sync_n8n_executions

# Send invoice reminders daily at 9 AM
0 9 * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py send_invoice_reminders

# Check workflow health every hour
0 * * * * cd /path/to/monoliet-portal && docker-compose exec -T django python manage.py check_workflow_health
```

## Access URLs

- **Admin Panel**: https://portal.monoliet.cloud/admin
- **Client Portal**: https://portal.monoliet.cloud/
- **API Root**: https://portal.monoliet.cloud/api/

## Security Features

- UUID primary keys (no sequential IDs exposed)
- Encrypted API credentials using Fernet
- Role-based permissions (admin vs client users)
- Client data isolation
- HTTPS enforced in production
- CSRF protection
- SQL injection prevention via Django ORM
- XSS prevention via template auto-escaping

## Email Notifications

Automatic emails sent for:
- New support tickets (to client and admin)
- Support ticket resolution (to client)
- New invoices (to client)
- Workflow errors (to admin)
- Invoice payment reminders

## Development

### Running Tests
```bash
docker-compose exec django python manage.py test
```

### Creating Migrations
```bash
docker-compose exec django python manage.py makemigrations
docker-compose exec django python manage.py migrate
```

### Accessing Django Shell
```bash
docker-compose exec django python manage.py shell
```

### Viewing Logs
```bash
# Django logs
docker-compose logs -f django

# PostgreSQL logs
docker-compose logs -f postgres

# All logs
docker-compose logs -f
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Static Files Not Loading
```bash
# Recollect static files
docker-compose exec django python manage.py collectstatic --noinput --clear
```

### Permission Denied Errors
```bash
# Fix ownership
sudo chown -R django:django /app
```

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Update `ALLOWED_HOSTS` with your domain
3. Generate a strong `SECRET_KEY`
4. Configure proper email settings
5. Set up SSL certificates via Nginx Proxy Manager
6. Enable database backups
7. Configure cron jobs for management commands
8. Monitor logs and set up error tracking

## Support

For issues or questions:
- Email: info@monoliet.cloud
- Create a support ticket in the portal

## License

Proprietary - Monoliet.cloud
