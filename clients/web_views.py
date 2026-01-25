"""
Web views for the Monoliet Client Portal.

This module provides Django template-based views for the client portal interface.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta

from .models import Client, Workflow, Execution, Invoice, SupportTicket
from .forms import SupportTicketForm


@login_required
def dashboard_view(request):
    """
    Dashboard view showing overview of client's workflows, executions, and invoices.
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return render(request, 'clients/no_client.html')

    client = request.user.client_profile.client

    # Get workflow stats
    workflows = client.workflows.all()
    active_workflows = workflows.filter(status='active').count()
    total_workflows = workflows.count()

    # Get recent executions (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_executions = client.executions.filter(
        execution_date__gte=thirty_days_ago
    ).order_by('-execution_date')[:10]

    # Calculate execution stats
    execution_stats = client.executions.filter(
        execution_date__gte=thirty_days_ago
    ).aggregate(
        total=Sum('total_count'),
        success=Sum('success_count'),
        error=Sum('error_count')
    )

    total_executions = execution_stats['total'] or 0
    success_rate = 0
    if total_executions > 0:
        success_rate = (execution_stats['success'] / total_executions) * 100

    # Get pending invoices
    pending_invoices = client.invoices.filter(status='pending').order_by('due_date')[:5]

    # Get open support tickets
    open_tickets = client.support_tickets.filter(
        status__in=['open', 'in_progress']
    ).order_by('-created_at')[:5]

    context = {
        'client': client,
        'active_workflows': active_workflows,
        'total_workflows': total_workflows,
        'recent_executions': recent_executions,
        'total_executions': total_executions,
        'success_rate': round(success_rate, 1),
        'pending_invoices': pending_invoices,
        'open_tickets': open_tickets,
    }

    return render(request, 'clients/dashboard.html', context)


@login_required
def workflows_view(request):
    """
    View showing all workflows for the client.
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return render(request, 'clients/no_client.html')

    client = request.user.client_profile.client

    # Get all workflows for the client
    workflows = client.workflows.all().order_by('-created_at')

    # Get execution stats for each workflow (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    for workflow in workflows:
        stats = workflow.executions.filter(
            execution_date__gte=thirty_days_ago
        ).aggregate(
            total=Sum('total_count'),
            success=Sum('success_count'),
            error=Sum('error_count')
        )
        workflow.recent_total = stats['total'] or 0
        workflow.recent_success = stats['success'] or 0
        workflow.recent_error = stats['error'] or 0
        if workflow.recent_total > 0:
            workflow.recent_success_rate = (workflow.recent_success / workflow.recent_total) * 100
        else:
            workflow.recent_success_rate = 0

    context = {
        'client': client,
        'workflows': workflows,
    }

    return render(request, 'clients/workflows.html', context)


@login_required
def invoices_view(request):
    """
    View showing all invoices for the client.
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return render(request, 'clients/no_client.html')

    client = request.user.client_profile.client

    # Get all invoices for the client
    invoices = client.invoices.all().order_by('-created_at')

    # Calculate totals
    total_amount = invoices.aggregate(Sum('amount'))['amount__sum'] or 0
    paid_amount = invoices.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_amount = invoices.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0
    overdue_amount = invoices.filter(
        status='pending',
        due_date__lt=date.today()
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Mark overdue invoices
    for invoice in invoices:
        invoice.is_overdue = invoice.status == 'pending' and invoice.due_date < date.today()

    context = {
        'client': client,
        'invoices': invoices,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'overdue_amount': overdue_amount,
    }

    return render(request, 'clients/invoices.html', context)


@login_required
def support_view(request):
    """
    View showing all support tickets for the client.
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return render(request, 'clients/no_client.html')

    client = request.user.client_profile.client

    # Get all support tickets for the client
    tickets = client.support_tickets.all().order_by('-created_at')

    # Calculate stats
    open_count = tickets.filter(status='open').count()
    in_progress_count = tickets.filter(status='in_progress').count()
    resolved_count = tickets.filter(status='resolved').count()

    context = {
        'client': client,
        'tickets': tickets,
        'open_count': open_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
    }

    return render(request, 'clients/support.html', context)


@login_required
def create_support_ticket_view(request):
    """
    View for creating a new support ticket.
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return render(request, 'clients/no_client.html')

    client = request.user.client_profile.client

    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.client = client
            ticket.save()
            messages.success(request, 'Support ticket created successfully!')
            return redirect('portal:support')
    else:
        form = SupportTicketForm()

    context = {
        'client': client,
        'form': form,
    }

    return render(request, 'clients/create_ticket.html', context)


@login_required
def executions_view(request):
    """
    Client portal execution view.

    Shows executions only for workflows linked to the client.
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return render(request, 'clients/no_client.html')

    client = request.user.client_profile.client

    # Get filter parameters
    workflow_id = request.GET.get('workflow')
    days = int(request.GET.get('days', 7))

    # Calculate date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    # Base queryset - only client's workflows
    executions = Execution.objects.filter(
        client=client,
        execution_date__gte=start_date,
        execution_date__lte=end_date
    ).select_related('workflow')

    # Apply workflow filter
    if workflow_id:
        executions = executions.filter(workflow__n8n_workflow_id=workflow_id)

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
    recent_executions = executions.order_by('-execution_date')[:50]

    # Get client's workflows for filter dropdown
    client_workflows = Workflow.objects.filter(client=client).order_by('workflow_name')

    context = {
        'client': client,
        'executions': recent_executions,
        'workflows': client_workflows,
        'total_executions': total_executions,
        'total_success': total_success,
        'total_errors': total_errors,
        'success_rate': round(success_rate, 1),
        'selected_workflow': workflow_id,
        'selected_days': days,
    }

    return render(request, 'clients/executions.html', context)


@login_required
def execution_detail_view(request, execution_id):
    """
    Client portal execution detail view.

    Only accessible if execution belongs to client's workflow.
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return render(request, 'clients/no_client.html')

    client = request.user.client_profile.client

    # Get execution, ensure it belongs to client
    execution = get_object_or_404(
        Execution.objects.select_related('workflow'),
        id=execution_id,
        client=client
    )

    # Calculate success rate
    success_rate = 0
    if execution.total_count > 0:
        success_rate = (execution.success_count / execution.total_count) * 100

    context = {
        'client': client,
        'execution': execution,
        'success_rate': round(success_rate, 1),
    }

    return render(request, 'clients/execution_detail.html', context)


@login_required
def execution_stats_api(request):
    """
    AJAX endpoint for client execution statistics.

    Returns stats for dashboard auto-refresh (client-filtered).
    """
    # Get client from user profile
    if not hasattr(request.user, 'client_profile') or not request.user.client_profile.client:
        return JsonResponse({'error': 'No client assigned'}, status=403)

    client = request.user.client_profile.client

    days = int(request.GET.get('days', 7))
    workflow_id = request.GET.get('workflow')

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    executions = Execution.objects.filter(
        client=client,
        execution_date__gte=start_date,
        execution_date__lte=end_date
    )

    if workflow_id:
        executions = executions.filter(workflow__n8n_workflow_id=workflow_id)

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
    })
