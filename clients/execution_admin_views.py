"""
Admin views for execution viewing and management.

Provides execution list, detail, and real-time monitoring
for the admin panel with Palantir-inspired design.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Q, Count
from datetime import datetime, timedelta
import logging

from .models import Execution, Workflow, Client
from .utils import get_n8n_client
from .execution_sync import ExecutionSyncService

logger = logging.getLogger(__name__)


@staff_member_required
def execution_dashboard(request):
    """
    Admin execution dashboard with overview and filters.

    Displays execution statistics, filters, and recent execution data
    in a Palantir-inspired interface.
    """
    # Get filter parameters
    workflow_id = request.GET.get('workflow')
    client_id = request.GET.get('client')
    days = int(request.GET.get('days', 7))

    # Calculate date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    # Base queryset
    executions = Execution.objects.filter(
        execution_date__gte=start_date,
        execution_date__lte=end_date
    ).select_related('workflow', 'workflow__client', 'client')

    # Apply filters
    if workflow_id:
        executions = executions.filter(workflow__n8n_workflow_id=workflow_id)
    if client_id:
        executions = executions.filter(client_id=client_id)

    # Calculate statistics
    stats = executions.aggregate(
        total=Sum('total_count'),
        success=Sum('success_count'),
        errors=Sum('error_count')
    )

    total_executions = stats['total'] or 0
    total_success = stats['success'] or 0
    total_errors = stats['errors'] or 0

    success_rate = 0
    if total_executions > 0:
        success_rate = (total_success / total_executions) * 100

    # Get recent executions
    recent_executions = executions.order_by('-execution_date', '-created_at')[:50]

    # Get workflows and clients for filter dropdowns
    workflows = Workflow.objects.all().order_by('workflow_name')
    clients = Client.objects.filter(status='active').order_by('company_name')

    context = {
        'title': 'Execution Dashboard',
        'executions': recent_executions,
        'workflows': workflows,
        'clients': clients,
        'total_executions': total_executions,
        'total_success': total_success,
        'total_errors': total_errors,
        'success_rate': round(success_rate, 1),
        'selected_workflow': workflow_id,
        'selected_client': client_id,
        'selected_days': days,
    }

    return render(request, 'admin/executions/dashboard.html', context)


@staff_member_required
def execution_detail(request, execution_id):
    """
    View detailed execution information.

    Shows detailed statistics for a specific execution record.
    """
    # Get execution from database
    execution = get_object_or_404(
        Execution.objects.select_related('workflow', 'client'),
        id=execution_id
    )

    # Calculate success rate for this execution
    success_rate = 0
    if execution.total_count > 0:
        success_rate = (execution.success_count / execution.total_count) * 100

    context = {
        'title': f'Execution Detail - {execution.execution_date}',
        'execution': execution,
        'success_rate': round(success_rate, 1),
    }

    return render(request, 'admin/executions/detail.html', context)


@staff_member_required
def sync_executions_view(request):
    """
    Trigger manual execution sync.

    Syncs execution data from n8n API to the database.
    """
    workflow_id = request.GET.get('workflow_id')

    service = ExecutionSyncService()

    try:
        if workflow_id:
            stats = service.sync_workflow_executions(workflow_id)
            messages.success(
                request,
                f"Synced executions for workflow: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['skipped']} skipped"
            )
        else:
            stats = service.sync_all_executions()
            messages.success(
                request,
                f"Synced all executions: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['skipped']} skipped"
            )
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        messages.error(request, f"Sync failed: {str(e)}")

    return redirect('execution_dashboard')


@staff_member_required
def execution_stats_api(request):
    """
    AJAX endpoint for execution statistics.

    Returns real-time stats for dashboard auto-refresh.
    """
    days = int(request.GET.get('days', 7))
    workflow_id = request.GET.get('workflow')
    client_id = request.GET.get('client')

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    executions = Execution.objects.filter(
        execution_date__gte=start_date,
        execution_date__lte=end_date
    )

    if workflow_id:
        executions = executions.filter(workflow__n8n_workflow_id=workflow_id)
    if client_id:
        executions = executions.filter(client_id=client_id)

    stats = executions.aggregate(
        total=Sum('total_count'),
        success=Sum('success_count'),
        errors=Sum('error_count')
    )

    total_executions = stats['total'] or 0
    total_success = stats['success'] or 0
    total_errors = stats['errors'] or 0

    success_rate = 0
    if total_executions > 0:
        success_rate = (total_success / total_executions) * 100

    return JsonResponse({
        'total_executions': total_executions,
        'total_success': total_success,
        'total_errors': total_errors,
        'success_rate': round(success_rate, 1),
        'timestamp': timezone.now().isoformat(),
    })


@staff_member_required
def execution_chart_data_api(request):
    """
    AJAX endpoint for execution chart data.

    Returns daily execution data for charts.
    """
    days = int(request.GET.get('days', 7))
    workflow_id = request.GET.get('workflow')
    client_id = request.GET.get('client')

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    executions = Execution.objects.filter(
        execution_date__gte=start_date,
        execution_date__lte=end_date
    )

    if workflow_id:
        executions = executions.filter(workflow__n8n_workflow_id=workflow_id)
    if client_id:
        executions = executions.filter(client_id=client_id)

    # Group by date
    daily_data = executions.values('execution_date').annotate(
        total=Sum('total_count'),
        success=Sum('success_count'),
        errors=Sum('error_count')
    ).order_by('execution_date')

    # Build response data
    labels = []
    success_data = []
    error_data = []

    for entry in daily_data:
        labels.append(entry['execution_date'].strftime('%Y-%m-%d'))
        success_data.append(entry['success'] or 0)
        error_data.append(entry['errors'] or 0)

    return JsonResponse({
        'labels': labels,
        'success': success_data,
        'errors': error_data,
    })
