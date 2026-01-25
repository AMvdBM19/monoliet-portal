"""
Management command to sync n8n executions to database.

Uses the ExecutionSyncService for consistent sync logic.

Usage:
    python manage.py sync_executions
    python manage.py sync_executions --workflow-id ABC123
    python manage.py sync_executions --limit 200
"""

from django.core.management.base import BaseCommand
from clients.execution_sync import ExecutionSyncService


class Command(BaseCommand):
    help = 'Sync n8n executions to Django database using ExecutionSyncService'

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
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        workflow_id = options.get('workflow_id')
        limit = min(options.get('limit', 100), 250)
        verbose = options.get('verbose', False)

        service = ExecutionSyncService()

        if workflow_id:
            self.stdout.write(f'Syncing executions for workflow {workflow_id}...')
            stats = service.sync_workflow_executions(workflow_id, limit)
        else:
            self.stdout.write(f'Syncing all recent executions (limit: {limit})...')
            stats = service.sync_all_executions(limit)

        # Display results
        if stats['errors'] > 0:
            self.stdout.write(self.style.WARNING(
                f"Sync completed with errors:"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Sync completed successfully:"
            ))

        self.stdout.write(f"  - Created: {stats['created']}")
        self.stdout.write(f"  - Updated: {stats['updated']}")
        self.stdout.write(f"  - Skipped: {stats['skipped']}")
        self.stdout.write(f"  - Errors:  {stats['errors']}")

        if verbose:
            self.stdout.write(self.style.NOTICE(
                "\nTip: Use --workflow-id to sync specific workflows"
            ))
