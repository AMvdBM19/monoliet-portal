# MCP Server Integration

## Overview

The Monoliet Portal now includes an integrated management interface for the MCP (Model Context Protocol) server. This allows administrators to manage n8n workflows directly from the Django admin panel.

## Architecture

```
┌─────────────────────────────────────┐
│      Django Monoliet Portal         │
│      (monoliet-portal repo)         │
│                                     │
│  ┌────────────────────────────────┐│
│  │   Admin Panel                  ││
│  │   /admin/mcp/                  ││
│  │   - Dashboard                  ││
│  │   - Workflows                  ││
│  │   - Health Monitoring          ││
│  └────────────────────────────────┘│
│              │                      │
│              │ HTTP REST API        │
│              │ (httpx client)       │
│              ▼                      │
└─────────────────────────────────────┘
              │
              │ Bearer Token Auth
              │
              ▼
┌─────────────────────────────────────┐
│   MCP Server Management API         │
│   (monoliet-mcp-server repo)        │
│   Port 8002                         │
│                                     │
│   Endpoints:                        │
│   - GET /health                     │
│   - GET /status                     │
│   - GET /workflows                  │
│   - GET /workflows/stats            │
│   - POST /workflows/{id}/activate   │
│   - POST /workflows/{id}/execute    │
└─────────────────────────────────────┘
              │
              │ n8n API
              ▼
┌─────────────────────────────────────┐
│          n8n Instance               │
│          Port 5678                  │
└─────────────────────────────────────┘
```

## Configuration

### 1. Enable MCP Integration

1. Navigate to Admin → Portal Settings
2. Scroll to the "MCP SERVER INTEGRATION" section
3. Enable "MCP Server Integration"
4. Set "MCP Management API URL" (e.g., `http://mcp-api.monoliet.cloud` or `http://localhost:8002`)
5. Optionally set auth token (if different from portal tokens)
6. Save settings

### 2. Access MCP Dashboard

- Navigate to `/admin/mcp/` or click "MCP SERVER MANAGEMENT" card on admin index
- View server status, workflow statistics, and recent activity
- Manage workflows (activate/deactivate/execute)

## Features

### Dashboard (`/admin/mcp/`)
- **Real-time server status**: Monitor MCP server health and connectivity
- **Workflow statistics**: Total, active, paused, and error workflows
- **Execution metrics**: Daily execution counts and success rates
- **n8n connection status**: Verify connectivity to n8n instance
- **Recent workflows list**: Quick view of latest workflows
- **Auto-refresh**: Dashboard updates every 30 seconds

### Workflows (`/admin/mcp/workflows/`)
- **List all n8n workflows**: Comprehensive workflow management
- **Filter by active status**: Focus on active or all workflows
- **Search by workflow name**: Quickly find specific workflows
- **Quick actions**:
  - Activate/deactivate workflows
  - Execute workflows manually
- **View workflow details**: ID, tags, status

## UI Design

The MCP interface follows the Palantir-inspired design system:

- **Colors:** Dark theme (`#0B0D10` background, `#FFFFFF` primary)
- **Typography:**
  - Space Grotesk (headings)
  - Space Mono (monospace)
  - Inter (body text)
- **Components:** Glassmorphic cards with backdrop blur
- **Status badges:** Color-coded
  - Green (operational)
  - Orange (degraded)
  - Red (offline)
  - Gray (unknown)
- **Data density:** Minimal, information-focused layout

## API Client (`clients/mcp_client.py`)

The `MCPClient` class handles all communication with the MCP server:

```python
from clients.mcp_client import get_mcp_client

# Get client instance (auto-configured from PortalSettings)
client = get_mcp_client()

# Health check
health = await client.health_check()

# Get workflows
workflows = await client.list_workflows(active_only=True)

# Execute workflow
result = await client.execute_workflow(workflow_id="abc123")
```

### Available Methods

- `health_check()`: Check MCP server health
- `get_status()`: Get comprehensive server status
- `get_workflow_stats()`: Get aggregated workflow statistics
- `list_workflows(active_only, search)`: List workflows with filtering
- `activate_workflow(workflow_id)`: Activate a workflow
- `deactivate_workflow(workflow_id)`: Deactivate a workflow
- `execute_workflow(workflow_id)`: Manually trigger workflow execution
- `get_config()`: Get MCP server configuration (redacted)

## Security

- **Authentication**: All MCP API calls require Bearer token authentication
- **Admin permissions**: Django admin permissions required (`@staff_member_required`)
- **CORS**: Configured for portal domains only
- **Data protection**: Sensitive data (n8n API keys) never exposed in responses
- **TLS/SSL encryption**: In production deployments

## Troubleshooting

### "MCP Server is not enabled"
**Solution:**
- Check Portal Settings → MCP Server Enabled
- Verify MCP Server URL is correct
- Save settings

### "Failed to connect to MCP server"
**Solution:**
- Ensure MCP server is running (`docker ps`)
- Check network connectivity
- Verify MCP server URL and port
- Check MCP server logs: `docker logs monoliet-mcp-server`

### Workflows not appearing
**Solution:**
- Verify n8n connection in MCP server
- Check n8n API key configuration
- Review MCP server logs for errors
- Test n8n API directly

### Connection timeout errors
**Solution:**
- Increase timeout in `mcp_client.py` (default: 10s)
- Check network latency
- Verify firewall rules

## Database Migration

After upgrading, run migrations to add MCP fields:

```bash
# In Docker container
docker exec -it monoliet-django python manage.py migrate

# Or locally
python manage.py migrate
```

Migration adds these fields to `PortalSettings`:
- `mcp_server_enabled` (BooleanField)
- `mcp_server_url` (URLField)
- `mcp_server_auth_token` (CharField)
- `mcp_last_health_check` (DateTimeField)
- `mcp_server_status` (CharField)

## Cross-Repository Coordination

This integration works with the **monoliet-mcp-server** repository:

### Portal Responsibilities
- Admin UI and API client
- Configuration storage in PortalSettings
- User authentication and permissions
- Palantir-inspired interface

### MCP Server Responsibilities
- REST API endpoints
- n8n integration
- Workflow management
- Health monitoring

### Communication
- HTTP REST API only
- No shared database
- No direct code coupling
- Bearer token authentication

## File Structure

```
monoliet-portal/
├── clients/
│   ├── mcp_client.py              # NEW: MCP API client
│   ├── mcp_admin_views.py         # NEW: Admin views
│   ├── models.py                  # MODIFIED: Added MCP fields
│   ├── admin.py                   # MODIFIED: Added MCP admin section
│   ├── admin_views.py             # MODIFIED: Added mcp_enabled context
│   └── templates/
│       └── admin/
│           ├── index.html         # MODIFIED: Added MCP card
│           └── mcp/               # NEW: MCP templates
│               ├── dashboard.html
│               └── workflows.html
├── portal/
│   └── urls.py                    # MODIFIED: Added MCP routes
├── requirements.txt               # MODIFIED: Added httpx
└── docs/
    └── MCP_INTEGRATION.md         # NEW: This file
```

## Development

### Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Configure Portal Settings:**
   - Login to admin
   - Go to Portal Settings
   - Enable MCP Server Integration
   - Set URL to `http://localhost:8002`

4. **Start MCP server** (in separate terminal):
   ```bash
   cd ../monoliet-mcp-server
   python main.py
   ```

5. **Access dashboard:**
   - Navigate to `/admin/mcp/`

### Testing

Test the integration:

```python
# In Django shell
python manage.py shell

from clients.mcp_client import get_mcp_client

client = get_mcp_client()
if client:
    import asyncio

    # Test health check
    health = asyncio.run(client.health_check())
    print(health)

    # Test workflow list
    workflows = asyncio.run(client.list_workflows())
    print(workflows)
```

## Deployment

### Docker Deployment

The integration works seamlessly with Docker deployments:

1. **Update environment variables** (if needed):
   ```env
   # .env
   MCP_SERVER_URL=http://mcp-server:8002
   ```

2. **Rebuild containers:**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Run migrations:**
   ```bash
   docker exec -it monoliet-django python manage.py migrate
   ```

### Nginx Proxy Manager

Ensure both services are accessible:

- **Portal**: `portal.monoliet.cloud` → `monoliet-django:8000`
- **MCP API**: `mcp-api.monoliet.cloud` → `monoliet-mcp-server:8002`

Configure CORS in MCP server to allow portal domain.

## Future Enhancements

Potential additions:
- Real-time workflow execution logs
- Advanced workflow creation/editing
- Execution history and analytics
- Workflow templates and cloning
- Scheduled workflow triggers
- Webhook configuration
- Multi-server support
- WebSocket connections for live updates

## Support

For issues or questions:
- **Portal issues**: monoliet-portal GitHub repository
- **MCP server issues**: monoliet-mcp-server GitHub repository
- **Integration issues**: Check both repositories

## License

Same license as Monoliet Portal project.
