"""
API views for the Monoliet Client Portal.

This module provides REST API endpoints for all models,
with proper permission handling for admin and client users.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse

from .models import (
    Client, Workflow, APICredential, Execution,
    Invoice, SupportTicket, ClientProfile
)
from .serializers import (
    ClientSerializer, ClientLimitedSerializer,
    WorkflowSerializer, APICredentialSerializer, APICredentialLimitedSerializer,
    ExecutionSerializer, ExecutionStatsSerializer,
    InvoiceSerializer, SupportTicketSerializer,
    ClientProfileSerializer, DashboardSerializer
)
from .permissions import (
    IsAdminUser, IsClientOwner, IsClientUser,
    CanCreateSupportTicket
)


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Client model.

    Admin users: Full CRUD access to all clients
    Client users: Read-only access to their own client data
    """
    queryset = Client.objects.all()
    filterset_fields = ['status', 'plan_tier', 'billing_cycle']
    search_fields = ['company_name', 'contact_name', 'email']
    ordering_fields = ['company_name', 'created_at', 'monthly_fee']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on user type."""
        if self.request.user.is_staff:
            return ClientSerializer
        return ClientLimitedSerializer

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['list', 'create', 'destroy']:
            permission_classes = [IsAdminUser]
        elif self.action == 'me':
            permission_classes = [IsClientUser]
        else:
            permission_classes = [IsClientOwner]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset based on user type."""
        if self.request.user.is_staff:
            return Client.objects.all()

        # Client users can only see their own client
        if hasattr(self.request.user, 'client_profile'):
            client_profile = self.request.user.client_profile
            if client_profile.client:
                return Client.objects.filter(id=client_profile.client.id)

        return Client.objects.none()

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get the current user's client information."""
        if not hasattr(request.user, 'client_profile'):
            return Response(
                {'error': 'User does not have a client profile'},
                status=status.HTTP_404_NOT_FOUND
            )

        client_profile = request.user.client_profile
        if not client_profile.client:
            return Response(
                {'error': 'User is not associated with a client'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(client_profile.client)
        return Response(serializer.data)


class WorkflowViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Workflow model.

    Admin users: Full CRUD access
    Client users: Read-only access to their workflows
    """
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    filterset_fields = ['status', 'client']
    search_fields = ['workflow_name', 'n8n_workflow_id']
    ordering_fields = ['workflow_name', 'created_at', 'last_execution']
    ordering = ['-created_at']

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsClientOwner | IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset based on user type."""
        if self.request.user.is_staff:
            return Workflow.objects.all()

        # Client users can only see their own workflows
        if hasattr(self.request.user, 'client_profile'):
            client_profile = self.request.user.client_profile
            if client_profile.client:
                return Workflow.objects.filter(client=client_profile.client)

        return Workflow.objects.none()

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def activate(self, request, pk=None):
        """Activate or pause a workflow."""
        workflow = self.get_object()
        new_status = request.data.get('status')

        if new_status not in ['active', 'paused']:
            return Response(
                {'error': 'Status must be either "active" or "paused"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        workflow.status = new_status
        workflow.save()

        serializer = self.get_serializer(workflow)
        return Response(serializer.data)


class APICredentialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for APICredential model.

    Admin users: Full access including encrypted data
    Client users: Limited view without encrypted data
    """
    queryset = APICredential.objects.all()
    filterset_fields = ['credential_type', 'status', 'client']
    search_fields = ['service_name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on user type."""
        if self.request.user.is_staff:
            return APICredentialSerializer
        return APICredentialLimitedSerializer

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsClientOwner | IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset based on user type."""
        if self.request.user.is_staff:
            return APICredential.objects.all()

        # Client users can only see their own credentials
        if hasattr(self.request.user, 'client_profile'):
            client_profile = self.request.user.client_profile
            if client_profile.client:
                return APICredential.objects.filter(client=client_profile.client)

        return APICredential.objects.none()


class ExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Execution model.

    Tracks daily execution statistics for workflows.
    """
    queryset = Execution.objects.all()
    serializer_class = ExecutionSerializer
    filterset_fields = ['execution_date', 'client', 'workflow']
    ordering = ['-execution_date']

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsClientOwner | IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset based on user type."""
        if self.request.user.is_staff:
            return Execution.objects.all()

        # Client users can only see their own executions
        if hasattr(self.request.user, 'client_profile'):
            client_profile = self.request.user.client_profile
            if client_profile.client:
                return Execution.objects.filter(client=client_profile.client)

        return Execution.objects.none()

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get execution statistics for a time period."""
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Filter executions
        queryset = self.get_queryset().filter(
            execution_date__range=[start_date, end_date]
        )

        # Calculate stats
        stats = queryset.aggregate(
            total_executions=Sum('total_count'),
            total_successes=Sum('success_count'),
            total_errors=Sum('error_count')
        )

        # Calculate success rate
        total = stats['total_executions'] or 0
        successes = stats['total_successes'] or 0
        success_rate = (successes / total * 100) if total > 0 else 0

        data = {
            'total_executions': total,
            'total_successes': successes,
            'total_errors': stats['total_errors'] or 0,
            'success_rate': round(success_rate, 2),
            'period_start': start_date,
            'period_end': end_date
        }

        serializer = ExecutionStatsSerializer(data)
        return Response(serializer.data)


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Invoice model.

    Admin users: Full CRUD access
    Client users: Read-only access to their invoices
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filterset_fields = ['status', 'type', 'client']
    search_fields = ['invoice_number']
    ordering = ['-created_at']

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsClientOwner | IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset based on user type."""
        if self.request.user.is_staff:
            return Invoice.objects.all()

        # Client users can only see their own invoices
        if hasattr(self.request.user, 'client_profile'):
            client_profile = self.request.user.client_profile
            if client_profile.client:
                return Invoice.objects.filter(client=client_profile.client)

        return Invoice.objects.none()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download invoice as PDF (placeholder for future implementation)."""
        invoice = self.get_object()

        # TODO: Implement PDF generation
        return Response({
            'message': 'PDF generation not yet implemented',
            'invoice_number': invoice.invoice_number
        })


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SupportTicket model.

    Both admin and client users can create tickets.
    Admin users can update ticket status.
    """
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    filterset_fields = ['status', 'priority', 'client']
    search_fields = ['subject', 'description']
    ordering = ['-created_at']

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == 'create':
            permission_classes = [CanCreateSupportTicket]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAdminUser]
        elif self.action == 'destroy':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsClientOwner | IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filter queryset based on user type."""
        if self.request.user.is_staff:
            return SupportTicket.objects.all()

        # Client users can only see their own tickets
        if hasattr(self.request.user, 'client_profile'):
            client_profile = self.request.user.client_profile
            if client_profile.client:
                return SupportTicket.objects.filter(client=client_profile.client)

        return SupportTicket.objects.none()

    def perform_create(self, serializer):
        """Automatically set the client when creating a ticket."""
        if not self.request.user.is_staff:
            # For client users, automatically set their client
            if hasattr(self.request.user, 'client_profile'):
                client_profile = self.request.user.client_profile
                if client_profile.client:
                    serializer.save(client=client_profile.client)
                    return

        serializer.save()

    def perform_update(self, serializer):
        """Set resolved_at timestamp when ticket is marked as resolved."""
        if serializer.validated_data.get('status') == 'resolved':
            if not serializer.instance.resolved_at:
                serializer.save(resolved_at=timezone.now())
            else:
                serializer.save()
        else:
            serializer.save()


class CustomAuthToken(ObtainAuthToken):
    """Custom authentication endpoint that returns user info along with token."""

    def post(self, request, *args, **kwargs):
        """Return token and user information."""
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        # Get client info if available
        client_data = None
        if hasattr(user, 'client_profile'):
            client_profile = user.client_profile
            if client_profile.client:
                client_data = {
                    'id': str(client_profile.client.id),
                    'company_name': client_profile.client.company_name
                }

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'client': client_data
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Logout endpoint that deletes the user's auth token."""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
