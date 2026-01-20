"""
Admin dashboard views for the Monoliet Client Portal.

This module provides analytics and metrics for the admin dashboard.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import Client, Workflow, Execution, Invoice, SupportTicket, PortalSettings


@staff_member_required
def admin_dashboard(request):
    """
    Provides data for the admin dashboard with analytics.
    """
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # Basic Stats
    total_clients = Client.objects.count()
    new_clients_this_month = Client.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()

    active_workflows = Workflow.objects.filter(status='active').count()
    total_workflows = Workflow.objects.count()

    # Revenue
    monthly_revenue = Invoice.objects.filter(
        status='paid',
        paid_date__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Executions
    executions_today = Execution.objects.filter(
        execution_date=now.date()
    ).aggregate(
        total=Sum('total_count'),
        success=Sum('success_count')
    )

    success_rate = 0
    if executions_today['total']:
        success_rate = round((executions_today['success'] / executions_today['total']) * 100)

    # Client Growth (last 6 months)
    client_growth_labels = []
    client_growth_data = []
    for i in range(6, 0, -1):
        month_start = now - timedelta(days=30*i)
        month_clients = Client.objects.filter(created_at__month=month_start.month).count()
        client_growth_labels.append(month_start.strftime('%b'))
        client_growth_data.append(month_clients)

    # Revenue (last 6 months)
    revenue_labels = []
    revenue_data = []
    for i in range(6, 0, -1):
        month_start = now - timedelta(days=30*i)
        month_revenue = Invoice.objects.filter(
            paid_date__month=month_start.month,
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        revenue_labels.append(month_start.strftime('%b'))
        revenue_data.append(float(month_revenue))

    # Workflow Status
    workflow_status = Workflow.objects.values('status').annotate(count=Count('id'))
    workflow_status_data = [0, 0, 0]  # active, paused, error
    for status in workflow_status:
        if status['status'] == 'active':
            workflow_status_data[0] = status['count']
        elif status['status'] == 'paused':
            workflow_status_data[1] = status['count']
        elif status['status'] == 'error':
            workflow_status_data[2] = status['count']

    # Executions (last 7 days)
    executions_labels = []
    executions_success = []
    executions_errors = []
    for i in range(7, 0, -1):
        day = now - timedelta(days=i)
        day_executions = Execution.objects.filter(execution_date=day.date()).aggregate(
            success=Sum('success_count'),
            errors=Sum('error_count')
        )
        executions_labels.append(day.strftime('%a'))
        executions_success.append(day_executions['success'] or 0)
        executions_errors.append(day_executions['errors'] or 0)

    # Check if MCP Server is enabled
    portal_settings = PortalSettings.objects.first()
    mcp_enabled = portal_settings and portal_settings.mcp_server_enabled

    context = {
        'total_clients': total_clients,
        'new_clients_this_month': new_clients_this_month,
        'active_workflows': active_workflows,
        'total_workflows': total_workflows,
        'monthly_revenue': round(monthly_revenue, 2),
        'revenue_growth': round(monthly_revenue * 0.15, 2),  # Placeholder
        'executions_today': executions_today['total'] or 0,
        'success_rate': success_rate,
        'client_growth_labels': client_growth_labels,
        'client_growth_data': client_growth_data,
        'revenue_labels': revenue_labels,
        'revenue_data': revenue_data,
        'workflow_status_data': workflow_status_data,
        'executions_labels': executions_labels,
        'executions_success': executions_success,
        'executions_errors': executions_errors,
        'mcp_enabled': mcp_enabled,  # NEW: MCP Server status
    }

    return render(request, 'admin/index.html', context)
