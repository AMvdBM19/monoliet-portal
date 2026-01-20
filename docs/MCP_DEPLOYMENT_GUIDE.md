# MCP Integration Deployment Guide

## Quick Start

This guide will help you deploy the MCP Server integration to your existing Monoliet Portal.

## Prerequisites

- Existing Monoliet Portal installation
- MCP Server running (see PROMPT_1_MCP_SERVER.md)
- Docker and Docker Compose (for production)
- Python 3.11+ (for local development)

## Deployment Steps

### Step 1: Update Dependencies

```bash
# Install new dependencies
pip install httpx==0.25.2

# Or in Docker
docker-compose build
```

### Step 2: Run Database Migration

The MCP integration adds new fields to the `PortalSettings` model.

**Local:**
```bash
python manage.py makemigrations clients --name add_mcp_server_settings
python manage.py migrate
```

**Docker:**
```bash
docker exec -it monoliet-django python manage.py makemigrations clients --name add_mcp_server_settings
docker exec -it monoliet-django python manage.py migrate
```

### Step 3: Configure Portal Settings

1. Login to Django admin: `/admin/`
2. Navigate to **Portal Settings**
3. Scroll to **MCP SERVER INTEGRATION** section
4. Configure:
   - ✅ Enable MCP Server Integration
   - Set **MCP Management API URL**: `http://mcp-server:8002` (Docker) or `http://localhost:8002` (local)
   - (Optional) Set **MCP Server Auth Token** if using custom authentication
5. Click **Save**

### Step 4: Verify Integration

1. Navigate to `/admin/mcp/` or click "MCP SERVER MANAGEMENT" on admin dashboard
2. You should see:
   - Server status
   - Workflow statistics
   - Recent workflows
3. If you see errors:
   - Check MCP server is running
   - Verify URL is correct
   - Check network connectivity

## Configuration Options

### Portal Settings Fields

| Field | Description | Example |
|-------|-------------|---------|
| `mcp_server_enabled` | Enable/disable MCP integration | `True` |
| `mcp_server_url` | MCP Management API URL | `http://mcp-server:8002` |
| `mcp_server_auth_token` | Optional auth token | Leave blank to use portal tokens |
| `mcp_server_status` | Current server status (auto-updated) | `operational` |
| `mcp_last_health_check` | Last health check timestamp (auto-updated) | `2024-01-15 10:30:00` |

### Environment Variables (Optional)

You can set environment variables for default configuration:

```env
# .env
MCP_SERVER_URL=http://mcp-api.monoliet.cloud
MCP_SERVER_ENABLED=True
```

Then reference in Django settings if needed.

## Docker Deployment

### docker-compose.yml

Ensure your MCP server is accessible from the Django container:

```yaml
version: '3.8'

services:
  django:
    build: .
    container_name: monoliet-django
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/monoliet
    networks:
      - monoliet-network

  mcp-server:
    image: monoliet-mcp-server:latest
    container_name: monoliet-mcp-server
    ports:
      - "8002:8002"
    environment:
      - N8N_API_URL=http://n8n:5678
      - N8N_API_KEY=${N8N_API_KEY}
    networks:
      - monoliet-network

networks:
  monoliet-network:
    driver: bridge
```

### Nginx Proxy Manager Routes

Configure reverse proxy for both services:

**Portal:**
- Domain: `portal.monoliet.cloud`
- Forward to: `monoliet-django:8000`
- Scheme: `http`

**MCP API:**
- Domain: `mcp-api.monoliet.cloud`
- Forward to: `monoliet-mcp-server:8002`
- Scheme: `http`

## Network Configuration

### Same Docker Network

If both services are on the same Docker network:

```
MCP Server URL: http://mcp-server:8002
```

### Separate Hosts

If MCP server is on a different host:

```
MCP Server URL: http://mcp-api.monoliet.cloud
```

### Local Development

```
MCP Server URL: http://localhost:8002
```

## Security Considerations

### 1. Authentication

MCP server requires Bearer token authentication. Options:

**Option A: Use Portal Tokens (Default)**
- Leave `mcp_server_auth_token` blank
- Portal will attempt to use Django admin user tokens
- Simplest option for internal deployments

**Option B: Custom Token**
- Generate a secure token for MCP server
- Set in Portal Settings: `mcp_server_auth_token`
- Configure same token in MCP server

### 2. Network Security

**Production:**
- Use HTTPS/TLS for all communications
- Configure firewall rules to restrict MCP API access
- Use private Docker networks

**Development:**
- HTTP is acceptable for localhost
- Still use authentication tokens

### 3. CORS Configuration

In MCP server, configure CORS to allow portal domain:

```python
# MCP Server: main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "https://portal.monoliet.cloud"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Migration Issues

**Error:** `django.db.utils.ProgrammingError: column does not exist`

**Solution:**
```bash
# Ensure migrations are run
python manage.py migrate clients

# If migration file doesn't exist, create it
python manage.py makemigrations clients --name add_mcp_server_settings
python manage.py migrate
```

### Connection Errors

**Error:** `Failed to connect to MCP server`

**Solutions:**
1. **Check MCP server is running:**
   ```bash
   docker ps | grep mcp-server
   # Should see running container
   ```

2. **Verify URL is correct:**
   - Docker: Use service name `http://mcp-server:8002`
   - Local: Use `http://localhost:8002`
   - Remote: Use full domain `http://mcp-api.monoliet.cloud`

3. **Test connectivity:**
   ```bash
   # From Django container
   docker exec -it monoliet-django curl http://mcp-server:8002/health
   ```

4. **Check logs:**
   ```bash
   docker logs monoliet-mcp-server
   ```

### Authentication Errors

**Error:** `401 Unauthorized`

**Solutions:**
1. **Verify auth token:**
   - Check `mcp_server_auth_token` in Portal Settings
   - Ensure it matches MCP server configuration

2. **Test authentication:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8002/health
   ```

### Template Errors

**Error:** `TemplateDoesNotExist: admin/mcp/dashboard.html`

**Solutions:**
1. **Verify template files exist:**
   ```bash
   ls clients/templates/admin/mcp/
   # Should show dashboard.html and workflows.html
   ```

2. **Check Django settings:**
   ```python
   # settings.py
   TEMPLATES = [{
       'DIRS': [],  # Django will find templates in app directories
       'APP_DIRS': True,  # Must be True
   }]
   ```

3. **Restart server:**
   ```bash
   docker-compose restart django
   ```

### Performance Issues

**Issue:** Dashboard loads slowly

**Solutions:**
1. **Increase timeout:**
   ```python
   # clients/mcp_client.py
   self.timeout = 30.0  # Increase from 10.0
   ```

2. **Check MCP server performance:**
   ```bash
   docker stats monoliet-mcp-server
   ```

3. **Optimize n8n queries** (in MCP server)

## Monitoring

### Health Checks

Monitor integration health:

```bash
# Check MCP server health
curl http://localhost:8002/health

# Check from Django shell
python manage.py shell
>>> from clients.mcp_client import get_mcp_client
>>> import asyncio
>>> client = get_mcp_client()
>>> asyncio.run(client.health_check())
```

### Logs

Monitor logs for issues:

```bash
# Django logs
docker logs -f monoliet-django

# MCP server logs
docker logs -f monoliet-mcp-server

# Filter for MCP-related logs
docker logs monoliet-django | grep MCP
```

### Status Dashboard

The MCP dashboard (`/admin/mcp/`) provides:
- Server status (operational/degraded/offline)
- Last health check timestamp
- Workflow statistics
- Auto-refresh every 30 seconds

## Rollback

If you need to rollback the integration:

### 1. Disable MCP Integration

1. Go to Portal Settings
2. Uncheck "Enable MCP Server Integration"
3. Save

The MCP card will disappear from admin dashboard.

### 2. Remove Database Fields (Optional)

If you want to completely remove MCP fields:

```bash
# Create reverse migration
python manage.py makemigrations clients --name remove_mcp_server_settings

# Edit migration file to remove fields
# Then run
python manage.py migrate
```

### 3. Revert Code Changes

```bash
git revert <commit-hash>
```

## Testing

### Manual Testing Checklist

- [ ] Portal Settings shows MCP SERVER INTEGRATION section
- [ ] Can enable/disable MCP integration
- [ ] Can set MCP server URL
- [ ] Admin dashboard shows MCP card when enabled
- [ ] MCP card disappears when disabled
- [ ] Clicking "OPEN MCP DASHBOARD" navigates to `/admin/mcp/`
- [ ] Dashboard displays server status
- [ ] Dashboard shows workflow statistics
- [ ] Can navigate to workflows page
- [ ] Can filter workflows by active status
- [ ] Can search workflows by name
- [ ] Can activate/deactivate workflows
- [ ] Can execute workflows manually
- [ ] Success messages appear after actions
- [ ] Error messages appear on failures

### Automated Testing

Create test cases:

```python
# clients/tests/test_mcp_integration.py
from django.test import TestCase
from clients.models import PortalSettings

class MCPIntegrationTest(TestCase):
    def test_portal_settings_mcp_fields(self):
        settings = PortalSettings.load()
        settings.mcp_server_enabled = True
        settings.mcp_server_url = "http://localhost:8002"
        settings.save()

        self.assertTrue(settings.mcp_server_enabled)
        self.assertEqual(settings.mcp_server_url, "http://localhost:8002")
```

## Performance Optimization

### 1. Caching

Cache MCP server status to reduce API calls:

```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### 2. Async Operations

The MCP client uses async operations for better performance. Ensure you're using `run_async()` helper in views.

### 3. Connection Pooling

httpx supports connection pooling by default, but you can tune it:

```python
# clients/mcp_client.py
async with httpx.AsyncClient(
    timeout=self.timeout,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
) as client:
    # ...
```

## Support

For issues or questions:
- Check documentation: `docs/MCP_INTEGRATION.md`
- Review logs: `docker logs monoliet-django`
- Test connectivity: `curl http://mcp-server:8002/health`
- Check GitHub issues in both repositories

## Next Steps

After successful deployment:

1. **Configure n8n workflows** in the MCP dashboard
2. **Set up monitoring** for health checks
3. **Create workflow templates** for common automation tasks
4. **Train team members** on using the MCP interface
5. **Review analytics** to optimize workflow performance

## Additional Resources

- [MCP Integration Overview](MCP_INTEGRATION.md)
- [MCP Server Setup](../../../monoliet-mcp-server/README.md)
- [Django Admin Documentation](https://docs.djangoproject.com/en/5.0/ref/contrib/admin/)
- [httpx Documentation](https://www.python-httpx.org/)
