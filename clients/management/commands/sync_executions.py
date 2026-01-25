"""
Management command to sync n8n executions to database.

Uses the ExecutionSyncService for consistent sync logic.

Usage:
    python manage.py sync_executions
    python manage.py sync_executions --workflow-id ABC123
    python manage.py sync_executions --limit 200
    python manage.py sync_executions --verbose
"""

from django.core.management.base import BaseCommand
from clients.execution_sync import ExecutionSyncService
from clients.models import Workflow
import logging


class Command(BaseCommand):
    help = 'Sync n8n executions to Django database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workflow-id',
            type=str,
            help='Sync executions for specific workflow only'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Max executions to fetch (default: 100, max: 250)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
        parser.add_argument(
            '--list-workflows',
            action='store_true',
            help='List all workflows in Django database'
        )

    def handle(self, *args, **options):
        workflow_id = options.get('workflow_id')
        limit = min(options.get('limit', 100), 250)
        verbose = options.get('verbose', False)
        list_workflows = options.get('list_workflows', False)

        # Set logging level
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
            logger = logging.getLogger('clients.execution_sync')
            logger.setLevel(logging.DEBUG)
            # Also configure root logger to show our messages
            logging.getLogger().setLevel(logging.DEBUG)

        # List workflows if requested
        if list_workflows:
            self._list_workflows()
            return

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        self.stdout.write(self.style.HTTP_INFO(' n8n Execution Sync'))
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        self.stdout.write('')

        service = ExecutionSyncService()

        if workflow_id:
            self.stdout.write(f'Syncing executions for workflow: {workflow_id}')
            self.stdout.write(f'Limit: {limit}')
            self.stdout.write('')
            stats = service.sync_workflow_executions(workflow_id, limit)
        else:
            self.stdout.write(f'Syncing all recent executions')
            self.stdout.write(f'Limit: {limit}')
            self.stdout.write('')
            stats = service.sync_all_executions(limit)

        # Display results
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('-' * 30))
        self.stdout.write(self.style.HTTP_INFO(' Results'))
        self.stdout.write(self.style.HTTP_INFO('-' * 30))

        # Created
        if stats['created'] > 0:
            self.stdout.write(self.style.SUCCESS(f"  Created: {stats['created']}"))
        else:
            self.stdout.write(f"  Created: {stats['created']}")

        # Updated
        if stats['updated'] > 0:
            self.stdout.write(self.style.SUCCESS(f"  Updated: {stats['updated']}"))
        else:
            self.stdout.write(f"  Updated: {stats['updated']}")

        # Skipped
        if stats['skipped'] > 0:
            self.stdout.write(self.style.WARNING(f"  Skipped: {stats['skipped']}"))
        else:
            self.stdout.write(f"  Skipped: {stats['skipped']}")

        # Errors
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"  Errors:  {stats['errors']}"))
        else:
            self.stdout.write(f"  Errors:  {stats['errors']}")

        self.stdout.write('')

        # Summary message
        if stats['errors'] > 0:
            self.stdout.write(self.style.WARNING(
                'Sync completed with errors. Check logs for details.'
            ))
        elif stats['created'] > 0 or stats['updated'] > 0:
            self.stdout.write(self.style.SUCCESS(
                'Sync completed successfully!'
            ))
        else:
            self.stdout.write(
                'No new execution data to sync.'
            )

        # Show helpful messages for skipped executions
        if stats['skipped'] > 0:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'Some executions were skipped because their workflows are not in the database.'
            ))
            self.stdout.write(
                'To fix this, create Workflow records with matching n8n_workflow_id values.'
            )
            self.stdout.write(
                'Run with --list-workflows to see workflows in the database.'
            )

        self.stdout.write('')

    def _list_workflows(self):
        """List all workflows in the Django database."""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        self.stdout.write(self.style.HTTP_INFO(' Workflows in Database'))
        self.stdout.write(self.style.HTTP_INFO('=' * 50))
        self.stdout.write('')

        workflows = Workflow.objects.all().select_related('client').order_by('workflow_name')

        if not workflows:
            self.stdout.write(self.style.WARNING('No workflows found in database.'))
            self.stdout.write('')
            self.stdout.write('Create Workflow records in the admin panel with:')
            self.stdout.write('  - n8n_workflow_id: The ID from n8n')
            self.stdout.write('  - client: The associated client')
            self.stdout.write('  - workflow_name: A descriptive name')
            return

        for workflow in workflows:
            status_style = self.style.SUCCESS if workflow.status == 'active' else self.style.WARNING
            self.stdout.write(
                f"  {workflow.n8n_workflow_id}: "
                f"{workflow.workflow_name} "
                f"[{status_style(workflow.status.upper())}] "
                f"({workflow.client.company_name})"
            )

        self.stdout.write('')
        self.stdout.write(f'Total: {workflows.count()} workflows')
        self.stdout.write('')
