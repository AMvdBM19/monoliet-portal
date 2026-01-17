"""
Django admin panel configuration for the Monoliet Client Portal.

This module configures the admin interface with custom displays,
filters, search fields, and actions for all models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime
import requests
from .models import (
    Client, Workflow, APICredential, Execution,
    Invoice, SupportTicket, ClientProfile, PortalSettings
)


class WorkflowInline(admin.TabularInline):
    """Inline editor for workflows within the Client admin."""
    model = Workflow
    extra = 0
    fields = ('workflow_name', 'n8n_workflow_id', 'status', 'execution_count')
    readonly_fields = ('execution_count',)


class InvoiceInline(admin.TabularInline):
    """Inline editor for invoices within the Client admin."""
    model = Invoice
    extra = 0
    fields = ('invoice_number', 'amount', 'type', 'status', 'due_date')
    readonly_fields = ('invoice_number',)


class SupportTicketInline(admin.TabularInline):
    """Inline editor for support tickets within the Client admin."""
    model = SupportTicket
    extra = 0
    fields = ('subject', 'status', 'priority', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Admin configuration for Client model."""

    list_display = (
        'company_name', 'contact_name', 'email',
        'status_badge', 'plan_tier', 'monthly_fee', 'next_billing_date'
    )
    list_filter = ('status', 'plan_tier', 'billing_cycle', 'created_at')
    search_fields = ('company_name', 'contact_name', 'email', 'phone')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'contact_name', 'email', 'phone')
        }),
        ('Plan & Billing', {
            'fields': ('status', 'plan_tier', 'setup_fee', 'monthly_fee', 'billing_cycle', 'next_billing_date')
        }),
        ('Internal Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [WorkflowInline, InvoiceInline, SupportTicketInline]
    actions = ['mark_as_churned', 'mark_as_active', 'send_welcome_email']

    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            'active': 'green',
            'paused': 'orange',
            'churned': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def mark_as_churned(self, request, queryset):
        """Mark selected clients as churned."""
        updated = queryset.update(status='churned')
        self.message_user(request, f'{updated} client(s) marked as churned.')
    mark_as_churned.short_description = 'Mark as churned'

    def mark_as_active(self, request, queryset):
        """Mark selected clients as active."""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} client(s) marked as active.')
    mark_as_active.short_description = 'Mark as active'

    def send_welcome_email(self, request, queryset):
        """Send welcome email to selected clients."""
        count = 0
        for client in queryset:
            try:
                send_mail(
                    subject='Welcome to Monoliet Automation Services',
                    message=f'Dear {client.contact_name},\n\nWelcome to Monoliet! We are excited to help automate your business processes.\n\nBest regards,\nThe Monoliet Team',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[client.email],
                    fail_silently=False,
                )
                count += 1
            except Exception as e:
                self.message_user(request, f'Failed to send email to {client.email}: {str(e)}', level='error')

        self.message_user(request, f'Welcome email sent to {count} client(s).')
    send_welcome_email.short_description = 'Send welcome email'


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin configuration for Workflow model."""

    list_display = (
        'workflow_name', 'client', 'status_badge',
        'n8n_workflow_link', 'execution_count', 'last_execution', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('workflow_name', 'n8n_workflow_id', 'client__company_name')
    readonly_fields = ('id', 'execution_count', 'last_execution', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Workflow Information', {
            'fields': ('client', 'workflow_name', 'n8n_workflow_id', 'n8n_workflow_url', 'description', 'status')
        }),
        ('Execution Statistics', {
            'fields': ('execution_count', 'last_execution')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            'active': 'green',
            'paused': 'orange',
            'error': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def n8n_workflow_link(self, obj):
        """Display clickable link to n8n workflow editor."""
        if obj.n8n_workflow_url:
            return format_html(
                '<a href="{}" target="_blank" style="'
                'background: rgba(255,255,255,0.1); '
                'color: #22C55E; '
                'padding: 6px 12px; '
                'border: 1px solid #22C55E; '
                'font-family: Space Mono, monospace; '
                'font-size: 0.75rem; '
                'text-transform: uppercase; '
                'text-decoration: none; '
                'display: inline-block;'
                '">OPEN IN n8n ↗</a>',
                obj.n8n_workflow_url
            )
        return format_html('<span style="color: #9B9B9B;">NO LINK</span>')
    n8n_workflow_link.short_description = 'n8n EDITOR'


@admin.register(APICredential)
class APICredentialAdmin(admin.ModelAdmin):
    """Admin configuration for APICredential model."""

    list_display = ('service_name', 'client', 'credential_type', 'status', 'last_verified', 'created_at')
    list_filter = ('credential_type', 'status', 'created_at')
    search_fields = ('service_name', 'client__company_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Credential Information', {
            'fields': ('client', 'service_name', 'credential_type', 'status')
        }),
        ('Encrypted Data', {
            'fields': ('encrypted_data',),
            'description': 'This data is encrypted. Handle with care.'
        }),
        ('Verification', {
            'fields': ('last_verified',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    """Admin configuration for Execution model."""

    list_display = (
        'workflow', 'client', 'execution_date',
        'total_count', 'success_count', 'error_count', 'success_rate'
    )
    list_filter = ('execution_date', 'client')
    search_fields = ('workflow__workflow_name', 'client__company_name')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'execution_date'

    fieldsets = (
        ('Execution Information', {
            'fields': ('client', 'workflow', 'execution_date')
        }),
        ('Execution Statistics', {
            'fields': ('total_count', 'success_count', 'error_count')
        }),
        ('System Information', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def success_rate(self, obj):
        """Calculate and display success rate."""
        if obj.total_count == 0:
            return format_html('<span style="color: gray;">N/A</span>')
        rate = (obj.success_count / obj.total_count) * 100
        if rate >= 90:
            color = 'green'
        elif rate >= 75:
            color = 'orange'
        else:
            color = 'red'
        percentage = f'{rate:.1f}%'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, percentage
        )
    success_rate.short_description = 'Success Rate'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin configuration for Invoice model."""

    list_display = (
        'invoice_number', 'client', 'amount', 'type',
        'status_badge', 'due_date', 'paid_date'
    )
    list_filter = ('status', 'type', 'created_at', 'due_date')
    search_fields = ('invoice_number', 'client__company_name', 'stripe_invoice_id')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'due_date'
    actions = ['mark_as_paid']

    fieldsets = (
        ('Invoice Information', {
            'fields': ('client', 'invoice_number', 'amount', 'type')
        }),
        ('Payment Status', {
            'fields': ('status', 'due_date', 'paid_date')
        }),
        ('Payment Integration', {
            'fields': ('stripe_invoice_id',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'overdue': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def mark_as_paid(self, request, queryset):
        """Mark selected invoices as paid."""
        updated = queryset.update(status='paid', paid_date=timezone.now().date())
        self.message_user(request, f'{updated} invoice(s) marked as paid.')
    mark_as_paid.short_description = 'Mark as paid'


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    """Admin configuration for SupportTicket model."""

    list_display = (
        'id', 'subject', 'client', 'status_badge',
        'priority_badge', 'created_at'
    )
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('subject', 'description', 'client__company_name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'resolved_at')
    date_hierarchy = 'created_at'
    actions = ['mark_as_resolved', 'mark_as_in_progress']

    fieldsets = (
        ('Ticket Information', {
            'fields': ('client', 'subject', 'description')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Resolution', {
            'fields': ('resolved_at',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status with color-coded badge."""
        colors = {
            'open': 'red',
            'in_progress': 'orange',
            'resolved': 'green'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def priority_badge(self, obj):
        """Display priority with color-coded badge."""
        colors = {
            'low': 'gray',
            'medium': 'blue',
            'high': 'red'
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'

    def mark_as_resolved(self, request, queryset):
        """Mark selected tickets as resolved."""
        updated = queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'{updated} ticket(s) marked as resolved.')
    mark_as_resolved.short_description = 'Mark as resolved'

    def mark_as_in_progress(self, request, queryset):
        """Mark selected tickets as in progress."""
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} ticket(s) marked as in progress.')
    mark_as_in_progress.short_description = 'Mark as in progress'


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """Admin configuration for ClientProfile model."""

    list_display = ('user', 'client', 'user_email', 'created_date')
    list_filter = ('client',)
    search_fields = ('user__username', 'user__email', 'client__company_name')
    raw_id_fields = ('user', 'client')

    def user_email(self, obj):
        """Display user's email."""
        return obj.user.email
    user_email.short_description = 'Email'

    def created_date(self, obj):
        """Display user's creation date."""
        return obj.user.date_joined
    created_date.short_description = 'Created'


@admin.register(PortalSettings)
class PortalSettingsAdmin(admin.ModelAdmin):
    """
    Custom admin for portal settings with n8n connection testing.
    """

    def has_add_permission(self, request):
        # Only allow one settings instance
        return not PortalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False

    def changelist_view(self, request, extra_context=None):
        # Redirect to change view for singleton
        obj = PortalSettings.load()
        return redirect(f'/admin/clients/portalsettings/{obj.pk}/change/')

    fieldsets = (
        ('n8n INTEGRATION', {
            'fields': (
                'n8n_api_url',
                'n8n_api_key',
                'n8n_connection_display',
            ),
            'classes': ('glass-container',),
        }),
        ('GENERAL SETTINGS', {
            'fields': (
                'company_name',
                'support_email',
                'max_clients',
            ),
            'classes': ('glass-container',),
        }),
        ('AUTOMATION', {
            'fields': (
                'enable_auto_sync',
                'sync_interval_minutes',
            ),
            'classes': ('glass-container',),
        }),
        ('NOTIFICATIONS', {
            'fields': (
                'slack_webhook_url',
                'enable_email_notifications',
            ),
            'classes': ('glass-container',),
        }),
    )

    readonly_fields = ['n8n_connection_display']

    def n8n_connection_display(self, obj):
        """Display n8n connection status with test button."""
        if obj.n8n_connection_status == 'connected':
            status_html = format_html(
                '<div style="'
                'background: rgba(34,197,94,0.2); '
                'border: 1px solid #22C55E; '
                'color: #22C55E; '
                'padding: 12px; '
                'border-radius: 4px; '
                'font-family: Space Mono, monospace; '
                'margin-bottom: 1rem;'
                '">'
                '✓ CONNECTED<br>'
                '<span style="font-size: 0.75rem; opacity: 0.8;">Last checked: {}</span>'
                '</div>',
                obj.n8n_last_checked.strftime('%Y-%m-%d %H:%M') if obj.n8n_last_checked else 'Never'
            )
        elif obj.n8n_connection_status == 'error':
            status_html = format_html(
                '<div style="'
                'background: rgba(239,68,68,0.2); '
                'border: 1px solid #EF4444; '
                'color: #EF4444; '
                'padding: 12px; '
                'border-radius: 4px; '
                'font-family: Space Mono, monospace; '
                'margin-bottom: 1rem;'
                '">'
                '✗ CONNECTION FAILED<br>'
                '<span style="font-size: 0.75rem;">Check API URL and key</span>'
                '</div>'
            )
        else:
            status_html = format_html(
                '<div style="'
                'background: rgba(155,155,155,0.2); '
                'border: 1px solid #9B9B9B; '
                'color: #9B9B9B; '
                'padding: 12px; '
                'border-radius: 4px; '
                'font-family: Space Mono, monospace; '
                'margin-bottom: 1rem;'
                '">'
                '○ NOT CONFIGURED<br>'
                '<span style="font-size: 0.75rem;">Enter API credentials</span>'
                '</div>'
            )

        # Add test button
        button_html = format_html(
            '<a href="{}" style="'
            'background: #FFFFFF; '
            'color: #1e1f2b; '
            'border: 1px solid #1e1f2b; '
            'padding: 12px 24px; '
            'font-family: Space Grotesk, sans-serif; '
            'text-transform: uppercase; '
            'text-decoration: none; '
            'display: inline-block; '
            'font-weight: 500; '
            'letter-spacing: 0.05em; '
            'transition: all 0.3s;'
            '" onmouseover="this.style.background=\'#1e1f2b\';this.style.color=\'#FFFFFF\';this.style.borderColor=\'#FFFFFF\';" '
            'onmouseout="this.style.background=\'#FFFFFF\';this.style.color=\'#1e1f2b\';this.style.borderColor=\'#1e1f2b\';">'
            'TEST CONNECTION'
            '</a>',
            f'/admin/clients/portalsettings/{obj.pk}/test-connection/'
        )

        return format_html('{}<br>{}', status_html, button_html)

    n8n_connection_display.short_description = 'CONNECTION STATUS'

    def get_urls(self):
        """Add custom URL for connection testing."""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/test-connection/',
                self.admin_site.admin_view(self.test_connection),
                name='test-n8n-connection'
            ),
        ]
        return custom_urls + urls

    def test_connection(self, request, object_id):
        """Test n8n API connection."""
        portal_settings = PortalSettings.objects.get(pk=object_id)

        if not portal_settings.n8n_api_key:
            messages.error(request, 'n8n API key not configured')
            return redirect(f'/admin/clients/portalsettings/{object_id}/change/')

        try:
            # Test API connection
            response = requests.get(
                f"{portal_settings.n8n_api_url}/workflows",
                headers={'X-N8N-API-KEY': portal_settings.n8n_api_key},
                timeout=5
            )

            if response.status_code == 200:
                portal_settings.n8n_connection_status = 'connected'
                portal_settings.n8n_last_checked = datetime.now()
                portal_settings.save()

                workflow_count = len(response.json().get('data', []))
                messages.success(
                    request,
                    f'✓ Connection successful! Found {workflow_count} workflows in n8n.'
                )
            else:
                portal_settings.n8n_connection_status = 'error'
                portal_settings.save()
                messages.error(
                    request,
                    f'✗ Connection failed: HTTP {response.status_code}'
                )

        except requests.exceptions.RequestException as e:
            portal_settings.n8n_connection_status = 'error'
            portal_settings.save()
            messages.error(request, f'✗ Connection error: {str(e)}')

        return redirect(f'/admin/clients/portalsettings/{object_id}/change/')

    class Media:
        css = {
            'all': ('css/style.css',)
        }
