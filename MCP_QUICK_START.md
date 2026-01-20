# MCP Integration - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Run Migration
```bash
# Local development
python manage.py migrate

# Docker deployment
docker exec -it monoliet-django python manage.py migrate
```

### Step 2: Enable MCP Integration
1. Login to Django admin: `/admin/`
2. Go to **Portal Settings**
3. Scroll to **MCP SERVER INTEGRATION**
4. ✅ Check "Enable MCP Server Integration"
5. Set **MCP Management API URL**:
   - Docker: `http://mcp-server:8002`
   - Local: `http://localhost:8002`
   - Remote: `http://mcp-api.monoliet.cloud`
6. Click **Save**

### Step 3: Access MCP Dashboard
- Navigate to `/admin/mcp/` OR
- Click "OPEN MCP DASHBOARD" button on admin home page

That's it! 🎉

---

## 📁 What Was Added

### New Files
- `clients/mcp_client.py` - API client for MCP server
- `clients/mcp_admin_views.py` - Dashboard and workflow views
- `clients/templates/admin/mcp/dashboard.html` - Dashboard UI
- `clients/templates/admin/mcp/workflows.html` - Workflows UI

### Modified Files
- `clients/models.py` - Added MCP fields to PortalSettings
- `clients/admin.py` - Added MCP admin section
- `portal/urls.py` - Added MCP routes
- `requirements.txt` - Added httpx dependency

---

## 🎨 Features

### Dashboard (`/admin/mcp/`)
- ⚡ Server status monitoring
- 📊 Workflow statistics
- 📈 Execution metrics
- 🔗 n8n connection status
- 🔄 Auto-refresh (30s)

### Workflows (`/admin/mcp/workflows/`)
- 📋 List all workflows
- 🔍 Search and filter
- ▶️ Activate/deactivate
- ⚙️ Execute manually

---

## 🔧 Troubleshooting

### "MCP Server is not enabled"
→ Go to Portal Settings and enable it

### "Failed to connect to MCP server"
```bash
# Check MCP server is running
docker ps | grep mcp-server

# Test connectivity
curl http://localhost:8002/health
```

### Migration errors
```bash
# Create migration if it doesn't exist
python manage.py makemigrations clients --name add_mcp_server_settings
python manage.py migrate
```

---

## 📚 Documentation

- **Full Guide**: `docs/MCP_INTEGRATION.md`
- **Deployment**: `docs/MCP_DEPLOYMENT_GUIDE.md`
- **Summary**: `IMPLEMENTATION_SUMMARY.md`

---

## 🔐 Security

- ✅ Admin authentication required
- ✅ Bearer token authentication for API
- ✅ No sensitive data exposure
- ✅ CORS configured

---

## 🎯 Quick Actions

### Test MCP Connection
```python
# Django shell
python manage.py shell

from clients.mcp_client import get_mcp_client
import asyncio

client = get_mcp_client()
health = asyncio.run(client.health_check())
print(health)
```

### View Workflows
```python
workflows = asyncio.run(client.list_workflows())
print(workflows)
```

### Execute Workflow
```python
result = asyncio.run(client.execute_workflow("workflow-id"))
print(result)
```

---

## 🚨 Important Notes

- **Zero Breaking Changes**: All existing functionality preserved
- **Optional Feature**: Disabled by default, enable when ready
- **Backward Compatible**: Safe to deploy
- **Production Ready**: Fully tested and documented

---

## 💡 Tips

1. **Enable MCP after MCP server is running** to avoid connection errors
2. **Use Docker service names** in docker-compose deployments
3. **Check server logs** if dashboard shows errors
4. **Refresh Portal Settings page** to see updated status

---

## ✅ Checklist

Before going live:
- [ ] MCP server is running
- [ ] Migration completed successfully
- [ ] Portal Settings configured
- [ ] Dashboard loads without errors
- [ ] Can view workflows
- [ ] Can execute test workflow
- [ ] Auto-refresh is working

---

**Need Help?** Check the full documentation in `docs/MCP_INTEGRATION.md`
