"""
Django REST Framework serializers for the Monoliet Client Portal API.

These serializers handle the conversion between Django models and JSON,
with different serializers for admin and client users to protect sensitive data.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Client, Workflow, APICredential, Execution,
    Invoice, SupportTicket, ClientProfile
)


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for Client model (admin view).

    Includes all fields including sensitive financial information.
    """
    workflows_count = serializers.IntegerField(source='workflows.count', read_only=True)
    active_workflows_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 'company_name', 'contact_name', 'email', 'phone',
            'status', 'plan_tier', 'setup_fee', 'monthly_fee',
            'billing_cycle', 'next_billing_date', 'notes',
            'workflows_count', 'active_workflows_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_active_workflows_count(self, obj):
        """Get count of active workflows."""
        return obj.workflows.filter(status='active').count()


class ClientLimitedSerializer(serializers.ModelSerializer):
    """
    Limited serializer for Client model (client user view).

    Excludes sensitive fields like setup_fee, monthly_fee, and notes.
    """
    workflows_count = serializers.IntegerField(source='workflows.count', read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'company_name', 'contact_name', 'email', 'phone',
            'status', 'plan_tier', 'billing_cycle', 'workflows_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkflowSerializer(serializers.ModelSerializer):
    """Serializer for Workflow model."""
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'client', 'client_name', 'workflow_name', 'n8n_workflow_id',
            'description', 'status', 'last_execution', 'execution_count',
            'success_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'execution_count', 'last_execution', 'created_at', 'updated_at']

    def get_success_rate(self, obj):
        """Calculate workflow success rate from recent executions."""
        from django.db.models import Sum
        recent_executions = obj.executions.all()[:30]  # Last 30 execution records

        totals = recent_executions.aggregate(
            total=Sum('total_count'),
            success=Sum('success_count')
        )

        if totals['total'] and totals['total'] > 0:
            return round((totals['success'] / totals['total']) * 100, 2)
        return None


class APICredentialSerializer(serializers.ModelSerializer):
    """
    Serializer for APICredential model (admin view).

    Includes encrypted data for admin users.
    """
    client_name = serializers.CharField(source='client.company_name', read_only=True)

    class Meta:
        model = APICredential
        fields = [
            'id', 'client', 'client_name', 'service_name', 'credential_type',
            'encrypted_data', 'status', 'last_verified',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class APICredentialLimitedSerializer(serializers.ModelSerializer):
    """
    Limited serializer for APICredential model (client user view).

    Excludes encrypted_data field for security.
    """
    client_name = serializers.CharField(source='client.company_name', read_only=True)

    class Meta:
        model = APICredential
        fields = [
            'id', 'client_name', 'service_name', 'credential_type',
            'status', 'last_verified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ExecutionSerializer(serializers.ModelSerializer):
    """Serializer for Execution model."""
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    workflow_name = serializers.CharField(source='workflow.workflow_name', read_only=True)
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = Execution
        fields = [
            'id', 'client', 'client_name', 'workflow', 'workflow_name',
            'execution_date', 'total_count', 'success_count', 'error_count',
            'success_rate', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_success_rate(self, obj):
        """Calculate success rate for this execution."""
        if obj.total_count > 0:
            return round((obj.success_count / obj.total_count) * 100, 2)
        return 0.0


class ExecutionStatsSerializer(serializers.Serializer):
    """Serializer for execution statistics."""
    total_executions = serializers.IntegerField()
    total_successes = serializers.IntegerField()
    total_errors = serializers.IntegerField()
    success_rate = serializers.FloatField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model."""
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'client', 'client_name', 'invoice_number', 'amount',
            'type', 'status', 'due_date', 'paid_date', 'is_overdue',
            'stripe_invoice_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at', 'updated_at']

    def get_is_overdue(self, obj):
        """Check if invoice is overdue."""
        from datetime import date
        return obj.status == 'pending' and obj.due_date < date.today()


class SupportTicketSerializer(serializers.ModelSerializer):
    """Serializer for SupportTicket model."""
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    days_open = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'client', 'client_name', 'subject', 'description',
            'status', 'priority', 'days_open', 'resolved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'resolved_at', 'created_at', 'updated_at']

    def get_days_open(self, obj):
        """Calculate how many days the ticket has been open."""
        from django.utils import timezone
        if obj.status == 'resolved' and obj.resolved_at:
            delta = obj.resolved_at - obj.created_at
        else:
            delta = timezone.now() - obj.created_at
        return delta.days


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']
        read_only_fields = ['id', 'is_staff']


class ClientProfileSerializer(serializers.ModelSerializer):
    """Serializer for ClientProfile model."""
    user = UserSerializer(read_only=True)
    client_name = serializers.CharField(source='client.company_name', read_only=True)

    class Meta:
        model = ClientProfile
        fields = ['id', 'user', 'client', 'client_name']
        read_only_fields = ['id']


class DashboardSerializer(serializers.Serializer):
    """
    Serializer for dashboard overview data.

    Aggregates key metrics for display on the client dashboard.
    """
    client = ClientLimitedSerializer()
    active_workflows = serializers.IntegerField()
    total_workflows = serializers.IntegerField()
    recent_executions = ExecutionSerializer(many=True)
    pending_invoices = InvoiceSerializer(many=True)
    open_tickets = SupportTicketSerializer(many=True)
    total_executions_last_30_days = serializers.IntegerField()
    success_rate_last_30_days = serializers.FloatField()
