"""
Tests for execution synchronization service.

Tests the ExecutionSyncService functionality including
n8n API integration and database sync operations.
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import date, datetime, timezone as dt_timezone

from clients.models import Workflow, Execution, Client


class ExecutionSyncServiceTestCase(TestCase):
    """Test cases for ExecutionSyncService."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a test client
        self.client_obj = Client.objects.create(
            company_name="Test Client",
            contact_name="Test Contact",
            email="test@example.com",
            plan_tier="Test Plan",
            setup_fee="100.00",
            monthly_fee="50.00",
            next_billing_date=date.today()
        )

        # Create a test workflow
        self.workflow = Workflow.objects.create(
            client=self.client_obj,
            workflow_name="Test Workflow",
            n8n_workflow_id="test-workflow-123",
            status='active'
        )

    @patch('clients.execution_sync.get_n8n_client')
    def test_sync_creates_execution_record(self, mock_get_client):
        """Test that syncing creates new execution records."""
        from clients.execution_sync import ExecutionSyncService

        # Mock n8n API response
        mock_client = MagicMock()
        mock_client.get_executions.return_value = {
            'data': [{
                'id': 1000,
                'workflowId': 'test-workflow-123',
                'status': 'success',
                'startedAt': '2024-01-20T10:00:00.000Z',
                'stoppedAt': '2024-01-20T10:00:05.000Z',
                'finished': True
            }]
        }
        mock_get_client.return_value = mock_client

        # Run sync
        service = ExecutionSyncService()
        stats = service.sync_all_executions()

        # Verify execution was created
        self.assertEqual(stats['created'], 1)
        self.assertTrue(
            Execution.objects.filter(workflow=self.workflow).exists()
        )

    @patch('clients.execution_sync.get_n8n_client')
    def test_sync_updates_existing_record(self, mock_get_client):
        """Test that syncing updates existing execution records."""
        from clients.execution_sync import ExecutionSyncService

        # Create existing execution
        exec_date = date(2024, 1, 20)
        Execution.objects.create(
            client=self.client_obj,
            workflow=self.workflow,
            execution_date=exec_date,
            total_count=5,
            success_count=4,
            error_count=1
        )

        # Mock n8n API response with same date
        mock_client = MagicMock()
        mock_client.get_executions.return_value = {
            'data': [
                {
                    'id': 1001,
                    'workflowId': 'test-workflow-123',
                    'status': 'success',
                    'startedAt': '2024-01-20T11:00:00.000Z',
                    'finished': True
                },
                {
                    'id': 1002,
                    'workflowId': 'test-workflow-123',
                    'status': 'error',
                    'startedAt': '2024-01-20T12:00:00.000Z',
                    'finished': True
                }
            ]
        }
        mock_get_client.return_value = mock_client

        # Run sync
        service = ExecutionSyncService()
        stats = service.sync_all_executions()

        # Verify execution was updated
        self.assertEqual(stats['updated'], 1)

        # Check updated values
        execution = Execution.objects.get(
            workflow=self.workflow,
            execution_date=exec_date
        )
        self.assertEqual(execution.total_count, 2)
        self.assertEqual(execution.success_count, 1)
        self.assertEqual(execution.error_count, 1)

    @patch('clients.execution_sync.get_n8n_client')
    def test_sync_skips_unknown_workflow(self, mock_get_client):
        """Test that syncing skips executions for unknown workflows."""
        from clients.execution_sync import ExecutionSyncService

        # Mock n8n API response with unknown workflow
        mock_client = MagicMock()
        mock_client.get_executions.return_value = {
            'data': [{
                'id': 1000,
                'workflowId': 'unknown-workflow-999',
                'status': 'success',
                'startedAt': '2024-01-20T10:00:00.000Z',
                'finished': True
            }]
        }
        mock_get_client.return_value = mock_client

        # Run sync
        service = ExecutionSyncService()
        stats = service.sync_all_executions()

        # Verify execution was skipped
        self.assertEqual(stats['skipped'], 1)
        self.assertEqual(stats['created'], 0)

    def test_parse_datetime_with_z_suffix(self):
        """Test datetime parsing with Z suffix."""
        from clients.execution_sync import ExecutionSyncService

        service = ExecutionSyncService()
        result = service._parse_datetime('2024-01-20T10:00:00.000Z')

        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 20)

    def test_parse_datetime_with_offset(self):
        """Test datetime parsing with timezone offset."""
        from clients.execution_sync import ExecutionSyncService

        service = ExecutionSyncService()
        result = service._parse_datetime('2024-01-20T10:00:00+00:00')

        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)

    def test_parse_datetime_invalid(self):
        """Test datetime parsing with invalid input."""
        from clients.execution_sync import ExecutionSyncService

        service = ExecutionSyncService()
        result = service._parse_datetime('invalid-date')

        self.assertIsNone(result)

    def test_parse_datetime_none(self):
        """Test datetime parsing with None input."""
        from clients.execution_sync import ExecutionSyncService

        service = ExecutionSyncService()
        result = service._parse_datetime(None)

        self.assertIsNone(result)

    def test_map_status_success(self):
        """Test status mapping for success."""
        from clients.execution_sync import ExecutionSyncService

        service = ExecutionSyncService()
        self.assertEqual(service._map_status('success'), 'success')

    def test_map_status_error(self):
        """Test status mapping for error states."""
        from clients.execution_sync import ExecutionSyncService

        service = ExecutionSyncService()
        self.assertEqual(service._map_status('error'), 'error')
        self.assertEqual(service._map_status('crashed'), 'error')

    def test_map_status_unknown(self):
        """Test status mapping for unknown status."""
        from clients.execution_sync import ExecutionSyncService

        service = ExecutionSyncService()
        self.assertEqual(service._map_status('unknown_status'), 'error')


class ExecutionAdminViewsTestCase(TestCase):
    """Test cases for admin execution views."""

    def setUp(self):
        """Set up test fixtures."""
        from django.contrib.auth.models import User

        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        # Create test client
        self.client_obj = Client.objects.create(
            company_name="Test Client",
            contact_name="Test Contact",
            email="test@example.com",
            plan_tier="Test Plan",
            setup_fee="100.00",
            monthly_fee="50.00",
            next_billing_date=date.today()
        )

        # Create test workflow
        self.workflow = Workflow.objects.create(
            client=self.client_obj,
            workflow_name="Test Workflow",
            n8n_workflow_id="test-workflow-123",
            status='active'
        )

        # Create test execution
        self.execution = Execution.objects.create(
            client=self.client_obj,
            workflow=self.workflow,
            execution_date=date.today(),
            total_count=10,
            success_count=8,
            error_count=2
        )

    def test_execution_dashboard_requires_auth(self):
        """Test that dashboard requires authentication."""
        response = self.client.get('/admin/executions/')
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_execution_dashboard_accessible_for_admin(self):
        """Test that admin can access dashboard."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/admin/executions/')
        self.assertEqual(response.status_code, 200)

    def test_execution_stats_api_returns_json(self):
        """Test that stats API returns JSON."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/admin/executions/api/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        data = response.json()
        self.assertIn('total_executions', data)
        self.assertIn('total_success', data)
        self.assertIn('total_errors', data)
        self.assertIn('success_rate', data)
