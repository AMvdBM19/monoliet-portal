"""
Admin dashboard views for the Monoliet Client Portal.

This module provides analytics and metrics for the admin dashboard.
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta
import json
import requests as http_requests
from .models import Client, Workflow, Execution, Invoice, SupportTicket, PortalSettings, AIConversation


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

    # Revenue snapshot
    from decimal import Decimal
    mrr = Client.objects.filter(status='active').aggregate(
        total=Sum('monthly_fee')
    )['total'] or Decimal('0.00')
    arr = mrr * 12
    overdue_revenue = Invoice.objects.filter(
        status='pending',
        due_date__lt=timezone.now().date()
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    pending_revenue = Invoice.objects.filter(
        status='pending'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

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
        'mcp_enabled': mcp_enabled,
        'mrr': round(mrr, 2),
        'arr': round(arr, 2),
        'overdue_revenue': round(overdue_revenue, 2),
        'pending_revenue': round(pending_revenue, 2),
    }

    return render(request, 'admin/index.html', context)


def build_admin_context(user):
    """Build system prompt context for the admin AI assistant."""
    total_clients = Client.objects.count()
    active_clients = Client.objects.filter(status='active').count()
    active_workflows = Workflow.objects.filter(status='active').count()
    error_workflows = Workflow.objects.filter(status='error').count()

    open_tickets = SupportTicket.objects.filter(status__in=['open', 'in_progress']).count()
    high_priority_tickets = SupportTicket.objects.filter(status='open', priority='high').count()

    from datetime import date
    overdue_invoices = Invoice.objects.filter(status='pending', due_date__lt=date.today()).count()
    pending_invoices = Invoice.objects.filter(status='pending').count()

    today = timezone.now().date()
    today_executions = Execution.objects.filter(execution_date=today).aggregate(
        total=Sum('total_count'),
        success=Sum('success_count'),
        errors=Sum('error_count')
    )

    return (
        "You are Monoliet's internal admin assistant. You help Andres manage the ERP/CRM portal. "
        "Be concise, direct, and use data when possible. "
        "Current state: " + str(total_clients) + " clients (" + str(active_clients) + " active), "
        + str(active_workflows) + " active workflows (" + str(error_workflows) + " in error), "
        + str(open_tickets) + " open support tickets (" + str(high_priority_tickets) + " high priority), "
        + str(pending_invoices) + " pending invoices (" + str(overdue_invoices) + " overdue), "
        "today's executions: " + str(today_executions['total'] or 0) + " total, "
        + str(today_executions['success'] or 0) + " success, " + str(today_executions['errors'] or 0) + " errors."
    )


@staff_member_required
@require_POST
def ai_chat_view(request):
    """AI assistant chat endpoint for admin panel."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_message = body.get('message', '').strip()
    conversation_id = body.get('conversation_id')

    if not user_message:
        return JsonResponse({'error': 'Message is required'}, status=400)

    from django.conf import settings as django_settings
    api_key = django_settings.ANTHROPIC_API_KEY
    if not api_key:
        return JsonResponse({'error': 'AI assistant not configured'}, status=503)

    # Get or create conversation
    if conversation_id:
        try:
            conversation = AIConversation.objects.get(id=conversation_id, user=request.user)
        except AIConversation.DoesNotExist:
            conversation = AIConversation.objects.create(
                user=request.user, context_type='admin'
            )
    else:
        conversation = AIConversation.objects.create(
            user=request.user, context_type='admin'
        )

    # Load existing messages
    messages_history = conversation.messages or []
    messages_history.append({'role': 'user', 'content': user_message})

    # Build system prompt
    system_prompt = build_admin_context(request.user)

    try:
        response = http_requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-sonnet-4-20250514',
                'max_tokens': 1024,
                'system': system_prompt,
                'messages': messages_history,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        reply = data['content'][0]['text']
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Save to conversation
    messages_history.append({'role': 'assistant', 'content': reply})
    conversation.messages = messages_history
    conversation.save()

    return JsonResponse({
        'reply': reply,
        'conversation_id': str(conversation.id),
    })
