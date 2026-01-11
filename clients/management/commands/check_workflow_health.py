"""
Management command to check workflow health and alert on errors.

This command:
- Checks all workflows for error status
- Monitors execution success rates
- Sends alerts to admin for workflows with issues

This command should be run hourly via cron.

Usage:
    python manage.py check_workflow_health [--threshold=80]
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum
from datetime import date, timedelta
from clients.models import Workflow, Execution


class Command(BaseCommand):
    help = 'Check workflow health and send alerts for issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=80,
            help='Success rate threshold percentage (default: 80)'
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        self.stdout.write(f'Checking workflow health (success rate threshold: {threshold}%)...')

        issues_found = []
        workflows_checked = 0

        # Get all active workflows
        active_workflows = Workflow.objects.filter(status__in=['active', 'error'])

        for workflow in active_workflows:
            workflows_checked += 1

            # Check 1: Workflow in error state
            if workflow.status == 'error':
                issues_found.append({
                    'workflow': workflow,
                    'issue_type': 'error_status',
                    'severity': 'high',
                    'message': f'Workflow is in ERROR state'
                })
                self.stdout.write(self.style.ERROR(
                    f'ERROR: {workflow.workflow_name} (Client: {workflow.client.company_name}) is in error state'
                ))

            # Check 2: Low success rate in last 7 days
            seven_days_ago = date.today() - timedelta(days=7)
            recent_executions = workflow.executions.filter(execution_date__gte=seven_days_ago)

            stats = recent_executions.aggregate(
                total=Sum('total_count'),
                success=Sum('success_count'),
                error=Sum('error_count')
            )

            total = stats['total'] or 0
            success = stats['success'] or 0

            if total > 0:
                success_rate = (success / total) * 100

                if success_rate < threshold:
                    issues_found.append({
                        'workflow': workflow,
                        'issue_type': 'low_success_rate',
                        'severity': 'medium',
                        'message': f'Success rate is {success_rate:.1f}% (below {threshold}% threshold)',
                        'stats': stats
                    })
                    self.stdout.write(self.style.WARNING(
                        f'WARNING: {workflow.workflow_name} has low success rate: {success_rate:.1f}%'
                    ))

            # Check 3: No recent executions (workflow might be stuck)
            if workflow.last_execution:
                days_since_last_execution = (date.today() - workflow.last_execution.date()).days

                if days_since_last_execution > 7:
                    issues_found.append({
                        'workflow': workflow,
                        'issue_type': 'no_recent_executions',
                        'severity': 'low',
                        'message': f'No executions in the last {days_since_last_execution} days'
                    })
                    self.stdout.write(self.style.WARNING(
                        f'WARNING: {workflow.workflow_name} has no executions in {days_since_last_execution} days'
                    ))

        # Send alert email if issues found
        if issues_found:
            self._send_alert_email(issues_found)
            self.stdout.write(self.style.WARNING(
                f'Found {len(issues_found)} issue(s) across {workflows_checked} workflows. Alert email sent.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'All {workflows_checked} workflows are healthy!'
            ))

    def _send_alert_email(self, issues):
        """Send alert email to admin with workflow issues."""

        # Group issues by severity
        high_severity = [i for i in issues if i['severity'] == 'high']
        medium_severity = [i for i in issues if i['severity'] == 'medium']
        low_severity = [i for i in issues if i['severity'] == 'low']

        # Build email message
        message = f'''Workflow Health Check Alert

{len(issues)} issue(s) detected:

'''

        if high_severity:
            message += f'HIGH SEVERITY ({len(high_severity)}):\n'
            for issue in high_severity:
                message += f'- {issue["workflow"].workflow_name} (Client: {issue["workflow"].client.company_name})\n'
                message += f'  Issue: {issue["message"]}\n'
                message += f'  n8n URL: {settings.N8N_URL}/workflow/{issue["workflow"].n8n_workflow_id}\n\n'

        if medium_severity:
            message += f'\nMEDIUM SEVERITY ({len(medium_severity)}):\n'
            for issue in medium_severity:
                message += f'- {issue["workflow"].workflow_name} (Client: {issue["workflow"].client.company_name})\n'
                message += f'  Issue: {issue["message"]}\n'
                if 'stats' in issue:
                    message += f'  Stats: {issue["stats"]["success"]} success / {issue["stats"]["error"]} errors / {issue["stats"]["total"]} total\n'
                message += f'  n8n URL: {settings.N8N_URL}/workflow/{issue["workflow"].n8n_workflow_id}\n\n'

        if low_severity:
            message += f'\nLOW SEVERITY ({len(low_severity)}):\n'
            for issue in low_severity:
                message += f'- {issue["workflow"].workflow_name} (Client: {issue["workflow"].client.company_name})\n'
                message += f'  Issue: {issue["message"]}\n\n'

        message += '\nPlease investigate these issues in the admin panel or n8n instance.\n'

        try:
            send_mail(
                subject=f'Workflow Health Alert: {len(issues)} Issue(s) Detected',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send alert email: {str(e)}'))
