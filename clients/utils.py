"""
Utility functions for the Monoliet Client Portal.

This module provides encryption/decryption for credentials,
invoice number generation, and n8n API integration.
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
from django.conf import settings
from decimal import Decimal


def encrypt_credential(data: dict) -> str:
    """
    Encrypt credential data using Fernet symmetric encryption.

    Args:
        data: Dictionary containing credential information

    Returns:
        Encrypted string representation of the data

    Raises:
        ValueError: If ENCRYPTION_KEY is not configured
    """
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not configured in settings")

    key = settings.ENCRYPTION_KEY.encode()
    cipher = Fernet(key)
    json_data = json.dumps(data)
    encrypted = cipher.encrypt(json_data.encode())
    return encrypted.decode()


def decrypt_credential(encrypted_data: str) -> dict:
    """
    Decrypt credential data.

    Args:
        encrypted_data: Encrypted string from database

    Returns:
        Dictionary containing decrypted credential information

    Raises:
        ValueError: If ENCRYPTION_KEY is not configured or decryption fails
    """
    if not settings.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY not configured in settings")

    key = settings.ENCRYPTION_KEY.encode()
    cipher = Fernet(key)
    try:
        decrypted = cipher.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())
    except Exception as e:
        raise ValueError(f"Failed to decrypt credential: {str(e)}")


def generate_invoice_number() -> str:
    """
    Generate a unique invoice number in format: INV-YYYY-XXX

    The number increments based on the current year and existing invoices.

    Returns:
        Formatted invoice number string (e.g., "INV-2024-001")
    """
    from clients.models import Invoice

    year = datetime.now().year

    # Get the last invoice number for this year
    last_invoice = Invoice.objects.filter(
        invoice_number__startswith=f'INV-{year}-'
    ).order_by('-invoice_number').first()

    if last_invoice:
        # Extract the sequence number and increment
        last_number = int(last_invoice.invoice_number.split('-')[-1])
        new_number = last_number + 1
    else:
        # First invoice of the year
        new_number = 1

    return f'INV-{year}-{new_number:03d}'


class N8NAPIClient:
    """
    Client for interacting with the n8n API.

    Provides methods to fetch workflow details and execution data.
    """

    def __init__(self):
        """Initialize the n8n API client with configured URL and API key."""
        self.base_url = settings.N8N_URL
        self.api_key = settings.N8N_API_KEY
        self.headers = {
            'X-N8N-API-KEY': self.api_key,
            'Accept': 'application/json',
        }

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """
        Make a request to the n8n API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data

        Returns:
            Response data as dictionary

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}/api/v1/{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"n8n API request failed: {str(e)}")

    def get_workflow(self, workflow_id: str) -> Dict:
        """
        Fetch workflow details from n8n.

        Args:
            workflow_id: The n8n workflow ID

        Returns:
            Dictionary containing workflow information
        """
        return self._make_request('GET', f'workflows/{workflow_id}')

    def get_workflows(self) -> List[Dict]:
        """
        Fetch all workflows from n8n.

        Returns:
            List of workflow dictionaries
        """
        result = self._make_request('GET', 'workflows')
        return result.get('data', [])

    def get_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        include_data: bool = False,
        cursor: Optional[str] = None
    ) -> Dict:
        """
        Fetch workflow executions from n8n.

        Args:
            workflow_id: Optional workflow ID to filter by
            status: Filter by status (success, error, running, waiting, canceled)
            limit: Maximum number of executions to return (max 250)
            include_data: Include full execution data in response
            cursor: Pagination cursor for fetching next page

        Returns:
            Dict containing 'data' list and optional 'nextCursor'
        """
        params = {
            'limit': min(limit, 250),
            'includeData': 'true' if include_data else 'false'
        }

        if workflow_id:
            params['workflowId'] = workflow_id
        if status:
            params['status'] = status
        if cursor:
            params['cursor'] = cursor

        return self._make_request('GET', 'executions', params=params)

    def get_executions_list(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch workflow executions as a simple list.

        Convenience method that returns just the data array.

        Args:
            workflow_id: Optional workflow ID to filter by
            status: Optional status filter
            limit: Maximum number of executions to return

        Returns:
            List of execution dictionaries
        """
        result = self.get_executions(
            workflow_id=workflow_id,
            status=status,
            limit=limit,
            include_data=False
        )
        return result.get('data', [])

    def get_execution(self, execution_id: str, include_data: bool = True) -> Dict:
        """
        Fetch a specific execution from n8n with detailed data.

        Args:
            execution_id: The execution ID
            include_data: Include full execution data/logs

        Returns:
            Dictionary containing execution details
        """
        params = {'includeData': 'true' if include_data else 'false'}
        return self._make_request('GET', f'executions/{execution_id}', params=params)

    def get_workflow_executions(
        self,
        workflow_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Fetch executions for a specific workflow.

        Convenience method for workflow-specific queries.

        Args:
            workflow_id: n8n workflow ID
            status: Optional status filter
            limit: Max results to return

        Returns:
            List of execution objects
        """
        return self.get_executions_list(
            workflow_id=workflow_id,
            status=status,
            limit=limit
        )

    def activate_workflow(self, workflow_id: str) -> Dict:
        """
        Activate a workflow in n8n.

        Args:
            workflow_id: The n8n workflow ID

        Returns:
            Dictionary containing updated workflow information
        """
        workflow = self.get_workflow(workflow_id)
        workflow['active'] = True
        return self._make_request('PUT', f'workflows/{workflow_id}', data=workflow)

    def deactivate_workflow(self, workflow_id: str) -> Dict:
        """
        Deactivate a workflow in n8n.

        Args:
            workflow_id: The n8n workflow ID

        Returns:
            Dictionary containing updated workflow information
        """
        workflow = self.get_workflow(workflow_id)
        workflow['active'] = False
        return self._make_request('PUT', f'workflows/{workflow_id}', data=workflow)


def sync_workflow_from_n8n(n8n_workflow_id: str) -> Dict:
    """
    Sync workflow data from n8n to update local database.

    Args:
        n8n_workflow_id: The n8n workflow ID

    Returns:
        Dictionary containing workflow data from n8n
    """
    client = N8NAPIClient()
    return client.get_workflow(n8n_workflow_id)


def calculate_monthly_revenue() -> Decimal:
    """
    Calculate total monthly recurring revenue from active clients.

    Returns:
        Total monthly revenue as Decimal
    """
    from clients.models import Client

    active_clients = Client.objects.filter(status='active')
    total_revenue = sum(client.monthly_fee for client in active_clients)
    return Decimal(str(total_revenue))


def get_overdue_invoices() -> List:
    """
    Get all overdue invoices.

    Returns:
        QuerySet of overdue Invoice objects
    """
    from clients.models import Invoice
    from datetime import date

    return Invoice.objects.filter(
        status='pending',
        due_date__lt=date.today()
    )


def get_n8n_client() -> N8NAPIClient:
    """
    Get an instance of the N8N API client.

    Returns:
        N8NAPIClient instance configured from settings
    """
    return N8NAPIClient()


def get_client_statistics(client_id: str) -> Dict:
    """
    Get comprehensive statistics for a specific client.

    Args:
        client_id: UUID of the client

    Returns:
        Dictionary containing client statistics
    """
    from clients.models import Client, Workflow, Execution, Invoice, SupportTicket
    from django.db.models import Sum, Count

    client = Client.objects.get(id=client_id)

    # Workflow stats
    total_workflows = client.workflows.count()
    active_workflows = client.workflows.filter(status='active').count()

    # Execution stats
    execution_stats = client.executions.aggregate(
        total_executions=Sum('total_count'),
        total_successes=Sum('success_count'),
        total_errors=Sum('error_count')
    )

    # Invoice stats
    invoice_stats = client.invoices.aggregate(
        total_invoiced=Sum('amount'),
        pending_amount=Sum('amount', filter=models.Q(status='pending'))
    )

    # Support ticket stats
    ticket_stats = client.support_tickets.aggregate(
        total_tickets=Count('id'),
        open_tickets=Count('id', filter=models.Q(status='open'))
    )

    return {
        'client': client,
        'workflows': {
            'total': total_workflows,
            'active': active_workflows,
        },
        'executions': {
            'total': execution_stats['total_executions'] or 0,
            'successes': execution_stats['total_successes'] or 0,
            'errors': execution_stats['total_errors'] or 0,
        },
        'invoices': {
            'total_amount': invoice_stats['total_invoiced'] or Decimal('0.00'),
            'pending_amount': invoice_stats['pending_amount'] or Decimal('0.00'),
        },
        'support_tickets': {
            'total': ticket_stats['total_tickets'] or 0,
            'open': ticket_stats['open_tickets'] or 0,
        }
    }
