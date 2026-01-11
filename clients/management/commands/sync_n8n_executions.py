"""
Management command to sync execution data from n8n to the Django database.

This command should be run daily via cron to keep execution statistics up to date.

Usage:
    python manage.py sync_n8n_executions [--days=7]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, date
from clients.models import Workflow, Execution
from clients.utils import N8NAPIClient


class Command(BaseCommand):
    help = 'Sync execution data from n8n to the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to sync (default: 7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        self.stdout.write(f'Syncing n8n execution data for the last {days} days...')

        try:
            client = N8NAPIClient()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize n8n client: {str(e)}'))
            return

        # Get all active workflows
        workflows = Workflow.objects.filter(status='active')
        total_synced = 0
        total_errors = 0

        for workflow in workflows:
            try:
                self.stdout.write(f'Syncing workflow: {workflow.workflow_name}')

                # Fetch executions from n8n
                executions = client.get_executions(workflow_id=workflow.n8n_workflow_id, limit=1000)

                # Group executions by date
                execution_by_date = {}

                for execution in executions:
                    # Parse execution data
                    finished_at = execution.get('finishedAt')
                    if not finished_at:
                        continue

                    # Convert to date
                    try:
                        exec_datetime = datetime.fromisoformat(finished_at.replace('Z', '+00:00'))
                        exec_date = exec_datetime.date()
                    except Exception:
                        continue

                    # Skip if older than requested days
                    if exec_date < date.today() - timedelta(days=days):
                        continue

                    # Initialize date entry
                    if exec_date not in execution_by_date:
                        execution_by_date[exec_date] = {
                            'total': 0,
                            'success': 0,
                            'error': 0
                        }

                    # Count execution
                    execution_by_date[exec_date]['total'] += 1

                    # Check if execution was successful
                    if execution.get('finished') and not execution.get('stoppedAt'):
                        execution_by_date[exec_date]['success'] += 1
                    else:
                        execution_by_date[exec_date]['error'] += 1

                # Update or create execution records
                for exec_date, stats in execution_by_date.items():
                    execution_record, created = Execution.objects.update_or_create(
                        workflow=workflow,
                        client=workflow.client,
                        execution_date=exec_date,
                        defaults={
                            'total_count': stats['total'],
                            'success_count': stats['success'],
                            'error_count': stats['error']
                        }
                    )
                    total_synced += 1
                    if created:
                        self.stdout.write(f'  Created execution record for {exec_date}')
                    else:
                        self.stdout.write(f'  Updated execution record for {exec_date}')

                # Update workflow last_execution and execution_count
                if executions:
                    latest_execution = max(executions, key=lambda x: x.get('finishedAt', ''))
                    try:
                        finished_at = latest_execution.get('finishedAt')
                        if finished_at:
                            last_exec_datetime = datetime.fromisoformat(finished_at.replace('Z', '+00:00'))
                            workflow.last_execution = last_exec_datetime
                    except Exception:
                        pass

                    workflow.execution_count = sum(stats['total'] for stats in execution_by_date.values())
                    workflow.save()

            except Exception as e:
                total_errors += 1
                self.stdout.write(self.style.ERROR(f'  Error syncing workflow {workflow.workflow_name}: {str(e)}'))
                continue

        self.stdout.write(self.style.SUCCESS(
            f'Sync complete! Synced {total_synced} execution records. Errors: {total_errors}'
        ))
