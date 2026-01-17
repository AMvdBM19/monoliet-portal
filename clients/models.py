"""
Database models for the Monoliet Client Portal.

This module defines all the core models for managing clients, workflows,
API credentials, executions, invoices, and support tickets.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Client(models.Model):
    """
    Represents a client company that uses Monoliet's n8n automation services.

    Each client has a plan tier, billing information, and status tracking.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('churned', 'Churned'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    plan_tier = models.CharField(max_length=100, help_text="e.g., 'E-commerce Essentials', 'Business Process'")
    setup_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    next_billing_date = models.DateField()
    notes = models.TextField(blank=True, help_text="Internal notes, hidden from client")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'

    def __str__(self):
        return f"{self.company_name} ({self.contact_name})"


class Workflow(models.Model):
    """
    Represents an n8n workflow associated with a client.

    Tracks workflow status, execution metrics, and links to the n8n instance.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='workflows')
    workflow_name = models.CharField(max_length=255)
    n8n_workflow_id = models.CharField(max_length=100, unique=True, help_text="n8n workflow ID")
    n8n_workflow_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Direct link to workflow in n8n editor"
    )
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_execution = models.DateTimeField(null=True, blank=True)
    execution_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Workflow'
        verbose_name_plural = 'Workflows'

    def __str__(self):
        return f"{self.workflow_name} - {self.client.company_name}"

    def save(self, *args, **kwargs):
        # Auto-generate n8n workflow URL if n8n_workflow_id exists
        if self.n8n_workflow_id and not self.n8n_workflow_url:
            self.n8n_workflow_url = f"https://n8n.monoliet.cloud/workflow/{self.n8n_workflow_id}"
        super().save(*args, **kwargs)


class APICredential(models.Model):
    """
    Stores encrypted API credentials for third-party services used in workflows.

    Credentials are encrypted before storage for security.
    """
    CREDENTIAL_TYPE_CHOICES = [
        ('oauth', 'OAuth'),
        ('api_key', 'API Key'),
        ('basic_auth', 'Basic Auth'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('invalid', 'Invalid'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='api_credentials')
    service_name = models.CharField(max_length=100, help_text="e.g., 'Shopify', 'Google Sheets'")
    credential_type = models.CharField(max_length=20, choices=CREDENTIAL_TYPE_CHOICES)
    encrypted_data = models.TextField(help_text="Encrypted JSON containing credentials")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_verified = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'API Credential'
        verbose_name_plural = 'API Credentials'

    def __str__(self):
        return f"{self.service_name} - {self.client.company_name}"


class Execution(models.Model):
    """
    Tracks daily execution statistics for workflows.

    Aggregates execution counts, successes, and errors on a daily basis.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='executions')
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    execution_date = models.DateField()
    total_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-execution_date']
        verbose_name = 'Execution'
        verbose_name_plural = 'Executions'
        unique_together = ['workflow', 'execution_date']

    def __str__(self):
        return f"{self.workflow.workflow_name} - {self.execution_date}"


class Invoice(models.Model):
    """
    Represents invoices for client billing.

    Tracks setup fees, monthly fees, and additional charges.
    """
    TYPE_CHOICES = [
        ('setup', 'Setup'),
        ('monthly', 'Monthly'),
        ('additional', 'Additional'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"{self.invoice_number} - {self.client.company_name}"


class SupportTicket(models.Model):
    """
    Represents customer support tickets.

    Clients can create tickets, and admins can track and resolve them.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'

    def __str__(self):
        return f"#{self.id} - {self.subject}"


class ClientProfile(models.Model):
    """
    Extends Django's User model to link portal users to their client records.

    This allows client users to access only their own data through the portal.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='users')

    class Meta:
        verbose_name = 'Client Profile'
        verbose_name_plural = 'Client Profiles'

    def __str__(self):
        if self.client:
            return f"{self.user.username} - {self.client.company_name}"
        return f"{self.user.username} - No Client Assigned"


class PortalSettings(models.Model):
    """
    Singleton model for portal configuration.
    Only one instance should exist.
    """
    # n8n Configuration
    n8n_api_url = models.URLField(
        max_length=500,
        default='https://n8n.monoliet.cloud/api/v1',
        help_text='n8n API base URL'
    )
    n8n_api_key = models.CharField(
        max_length=500,
        blank=True,
        help_text='n8n API authentication key'
    )
    n8n_connection_status = models.CharField(
        max_length=20,
        choices=[
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('error', 'Error'),
        ],
        default='disconnected'
    )
    n8n_last_checked = models.DateTimeField(blank=True, null=True)

    # General Settings
    company_name = models.CharField(
        max_length=255,
        default='Monoliet',
        help_text='Your company name'
    )
    support_email = models.EmailField(
        default='info@monoliet.cloud',
        help_text='Support contact email'
    )
    max_clients = models.IntegerField(
        default=100,
        help_text='Maximum number of clients allowed'
    )
    enable_auto_sync = models.BooleanField(
        default=True,
        help_text='Automatically sync n8n data'
    )
    sync_interval_minutes = models.IntegerField(
        default=15,
        help_text='Minutes between automatic syncs'
    )

    # Notification Settings
    slack_webhook_url = models.URLField(
        max_length=500,
        blank=True,
        help_text='Slack webhook for notifications'
    )
    enable_email_notifications = models.BooleanField(
        default=True,
        help_text='Send email notifications'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Portal Settings'
        verbose_name_plural = 'Portal Settings'

    def __str__(self):
        return 'Portal Configuration'

    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton pattern)
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion
        pass

    @classmethod
    def load(cls):
        """Load the singleton instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
