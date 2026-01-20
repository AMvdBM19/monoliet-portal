"""
Admin views for MCP Server management.

Provides Palantir-inspired interface for managing the MCP server
directly from the Django admin panel.
"""

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
import asyncio
import logging
from .mcp_client import get_mcp_client
from .models import PortalSettings

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync views."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@staff_member_required
def mcp_dashboard(request):
    """
    MCP Server dashboard view.

    Displays:
    - Server status and health
    - Workflow statistics
    - Recent activity
    - Quick actions
    """
    context = {
        'title': 'MCP Server Management',
        'mcp_enabled': False,
        'error': None,
        'server_status': None,
        'workflow_stats': None,
        'workflows': [],
    }

    # Get MCP client
    client = get_mcp_client()
    if not client:
        context['error'] = "MCP Server is not enabled. Configure in Portal Settings."
        return render(request, 'admin/mcp/dashboard.html', context)

    context['mcp_enabled'] = True

    # Fetch data from MCP server
    try:
        # Health check
        health = run_async(client.health_check())

        # Server status
        status = run_async(client.get_status())
        context['server_status'] = status

        # Update PortalSettings with latest status
        portal_settings = PortalSettings.objects.first()
        if portal_settings:
            portal_settings.mcp_last_health_check = timezone.now()
            portal_settings.mcp_server_status = status.get('status', 'unknown')
            portal_settings.save()

        # Workflow statistics
        stats = run_async(client.get_workflow_stats())
        context['workflow_stats'] = stats

        # Recent workflows
        workflows_data = run_async(client.list_workflows())
        context['workflows'] = workflows_data.get('workflows', [])[:10]  # Top 10

    except Exception as e:
        logger.error(f"Failed to fetch MCP server data: {e}")
        context['error'] = f"Failed to connect to MCP server: {str(e)}"

    return render(request, 'admin/mcp/dashboard.html', context)


@staff_member_required
def mcp_workflows(request):
    """
    MCP Workflows management view.

    Lists all workflows with filtering and management actions.
    """
    context = {
        'title': 'MCP Workflows',
        'workflows': [],
        'error': None,
    }

    client = get_mcp_client()
    if not client:
        context['error'] = "MCP Server is not enabled."
        return render(request, 'admin/mcp/workflows.html', context)

    # Get filters from request
    active_only = request.GET.get('active_only') == 'true'
    search = request.GET.get('search', '')

    try:
        workflows_data = run_async(client.list_workflows(
            active_only=active_only,
            search=search if search else None
        ))
        context['workflows'] = workflows_data.get('workflows', [])
        context['total_count'] = workflows_data.get('count', 0)
    except Exception as e:
        logger.error(f"Failed to fetch workflows: {e}")
        context['error'] = str(e)

    return render(request, 'admin/mcp/workflows.html', context)


@staff_member_required
def mcp_workflow_action(request, workflow_id, action):
    """
    Execute action on a workflow.

    Actions: activate, deactivate, execute
    """
    client = get_mcp_client()
    if not client:
        messages.error(request, "MCP Server is not enabled.")
        return redirect('admin:mcp_dashboard')

    try:
        if action == 'activate':
            result = run_async(client.activate_workflow(workflow_id))
            messages.success(request, f"Workflow activated successfully.")
        elif action == 'deactivate':
            result = run_async(client.deactivate_workflow(workflow_id))
            messages.success(request, f"Workflow deactivated successfully.")
        elif action == 'execute':
            result = run_async(client.execute_workflow(workflow_id))
            execution_id = result.get('execution_id', 'unknown')
            messages.success(request, f"Workflow executed. Execution ID: {execution_id}")
        else:
            messages.error(request, f"Unknown action: {action}")
    except Exception as e:
        logger.error(f"Workflow action failed: {e}")
        messages.error(request, f"Action failed: {str(e)}")

    # Redirect back to workflows page
    return redirect('admin:mcp_workflows')


@staff_member_required
def mcp_health_check(request):
    """
    AJAX endpoint for health check.

    Returns JSON with current health status.
    """
    client = get_mcp_client()
    if not client:
        return JsonResponse({
            'healthy': False,
            'error': 'MCP Server not enabled'
        })

    try:
        health = run_async(client.health_check())
        return JsonResponse(health)
    except Exception as e:
        return JsonResponse({
            'healthy': False,
            'error': str(e)
        })


@staff_member_required
def mcp_stats_api(request):
    """
    AJAX endpoint for workflow statistics.

    Used for real-time dashboard updates.
    """
    client = get_mcp_client()
    if not client:
        return JsonResponse({'error': 'MCP Server not enabled'}, status=400)

    try:
        stats = run_async(client.get_workflow_stats())
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
