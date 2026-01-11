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
from .models import (
    Client, Workflow, APICredential, Execution,
    Invoice, SupportTicket, ClientProfile
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
        'execution_count', 'last_execution', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('workflow_name', 'n8n_workflow_id', 'client__company_name')
    readonly_fields = ('id', 'execution_count', 'last_execution', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Workflow Information', {
            'fields': ('client', 'workflow_name', 'n8n_workflow_id', 'description', 'status')
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
            return 'N/A'
        rate = (obj.success_count / obj.total_count) * 100
        color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            rate
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
