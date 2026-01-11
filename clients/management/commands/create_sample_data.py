"""
Management command to create sample data for testing.

Creates sample clients, workflows, executions, invoices, and support tickets.

Usage:
    python manage.py create_sample_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from clients.models import (
    Client, Workflow, APICredential, Execution,
    Invoice, SupportTicket, ClientProfile
)
from clients.utils import encrypt_credential


class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        # Create sample clients
        clients_data = [
            {
                'company_name': 'Acme E-commerce',
                'contact_name': 'John Smith',
                'email': 'john@acme-ecommerce.com',
                'phone': '+1-555-0100',
                'plan_tier': 'E-commerce Essentials',
                'setup_fee': Decimal('500.00'),
                'monthly_fee': Decimal('247.00'),
                'billing_cycle': 'monthly',
                'next_billing_date': date.today() + timedelta(days=15),
                'notes': 'Shopify integration, email marketing automation'
            },
            {
                'company_name': 'Digital Marketing Pro',
                'contact_name': 'Sarah Johnson',
                'email': 'sarah@digitalmarketingpro.com',
                'phone': '+1-555-0101',
                'plan_tier': 'Business Process',
                'setup_fee': Decimal('750.00'),
                'monthly_fee': Decimal('397.00'),
                'billing_cycle': 'monthly',
                'next_billing_date': date.today() + timedelta(days=22),
                'notes': 'Facebook Ads, Google Sheets, Slack integration'
            },
            {
                'company_name': 'TechStart Inc',
                'contact_name': 'Mike Chen',
                'email': 'mike@techstart.io',
                'phone': '+1-555-0102',
                'plan_tier': 'Custom Enterprise',
                'setup_fee': Decimal('1200.00'),
                'monthly_fee': Decimal('597.00'),
                'billing_cycle': 'yearly',
                'next_billing_date': date.today() + timedelta(days=330),
                'notes': 'Custom API integrations, multiple workflows'
            },
        ]

        clients = []
        for client_data in clients_data:
            client, created = Client.objects.get_or_create(
                email=client_data['email'],
                defaults=client_data
            )
            clients.append(client)
            if created:
                self.stdout.write(f'Created client: {client.company_name}')

        # Create sample workflows
        workflows_data = [
            {
                'client': clients[0],
                'workflow_name': 'Shopify Order Sync',
                'n8n_workflow_id': 'shopify-order-sync-001',
                'description': 'Syncs new orders from Shopify to Google Sheets',
                'status': 'active'
            },
            {
                'client': clients[0],
                'workflow_name': 'Customer Email Campaign',
                'n8n_workflow_id': 'email-campaign-001',
                'description': 'Automated email campaigns for new customers',
                'status': 'active'
            },
            {
                'client': clients[1],
                'workflow_name': 'Facebook Ads Reporter',
                'n8n_workflow_id': 'fb-ads-reporter-001',
                'description': 'Daily Facebook Ads performance reports to Slack',
                'status': 'active'
            },
            {
                'client': clients[1],
                'workflow_name': 'Lead Capture Automation',
                'n8n_workflow_id': 'lead-capture-001',
                'description': 'Captures leads from website and adds to CRM',
                'status': 'active'
            },
            {
                'client': clients[2],
                'workflow_name': 'API Data Sync',
                'n8n_workflow_id': 'api-sync-001',
                'description': 'Syncs data between multiple APIs',
                'status': 'active'
            },
            {
                'client': clients[2],
                'workflow_name': 'Error Monitoring',
                'n8n_workflow_id': 'error-monitor-001',
                'description': 'Monitors system errors and sends alerts',
                'status': 'error'
            },
        ]

        workflows = []
        for workflow_data in workflows_data:
            workflow, created = Workflow.objects.get_or_create(
                n8n_workflow_id=workflow_data['n8n_workflow_id'],
                defaults=workflow_data
            )
            workflows.append(workflow)
            if created:
                self.stdout.write(f'Created workflow: {workflow.workflow_name}')

        # Create sample executions (last 30 days)
        self.stdout.write('Creating execution records...')
        execution_count = 0
        for workflow in workflows[:5]:  # Skip the error workflow
            for days_ago in range(30):
                exec_date = date.today() - timedelta(days=days_ago)
                total = random.randint(10, 100)
                success = int(total * random.uniform(0.85, 0.99))
                error = total - success

                Execution.objects.get_or_create(
                    workflow=workflow,
                    client=workflow.client,
                    execution_date=exec_date,
                    defaults={
                        'total_count': total,
                        'success_count': success,
                        'error_count': error
                    }
                )
                execution_count += 1

        self.stdout.write(f'Created {execution_count} execution records')

        # Update workflow statistics
        for workflow in workflows:
            workflow.execution_count = workflow.executions.count()
            if workflow.executions.exists():
                workflow.last_execution = timezone.now() - timedelta(hours=random.randint(1, 24))
            workflow.save()

        # Create sample invoices
        invoices_data = [
            # Client 1
            {'client': clients[0], 'type': 'setup', 'amount': clients[0].setup_fee, 'status': 'paid', 'due_date': date.today() - timedelta(days=60), 'paid_date': date.today() - timedelta(days=58)},
            {'client': clients[0], 'type': 'monthly', 'amount': clients[0].monthly_fee, 'status': 'paid', 'due_date': date.today() - timedelta(days=30), 'paid_date': date.today() - timedelta(days=28)},
            {'client': clients[0], 'type': 'monthly', 'amount': clients[0].monthly_fee, 'status': 'pending', 'due_date': date.today() + timedelta(days=5), 'paid_date': None},
            # Client 2
            {'client': clients[1], 'type': 'setup', 'amount': clients[1].setup_fee, 'status': 'paid', 'due_date': date.today() - timedelta(days=45), 'paid_date': date.today() - timedelta(days=44)},
            {'client': clients[1], 'type': 'monthly', 'amount': clients[1].monthly_fee, 'status': 'pending', 'due_date': date.today() + timedelta(days=10), 'paid_date': None},
            # Client 3
            {'client': clients[2], 'type': 'setup', 'amount': clients[2].setup_fee, 'status': 'paid', 'due_date': date.today() - timedelta(days=330), 'paid_date': date.today() - timedelta(days=328)},
        ]

        for invoice_data in invoices_data:
            from clients.utils import generate_invoice_number
            invoice_data['invoice_number'] = generate_invoice_number()
            invoice, created = Invoice.objects.get_or_create(
                invoice_number=invoice_data['invoice_number'],
                defaults=invoice_data
            )
            if created:
                self.stdout.write(f'Created invoice: {invoice.invoice_number}')

        # Create sample support tickets
        tickets_data = [
            {'client': clients[0], 'subject': 'Workflow not syncing orders', 'description': 'The Shopify order sync workflow stopped working yesterday. Can you help?', 'status': 'resolved', 'priority': 'high'},
            {'client': clients[0], 'subject': 'Add new product field to sync', 'description': 'Can we add the product SKU field to the order sync?', 'status': 'open', 'priority': 'medium'},
            {'client': clients[1], 'subject': 'Facebook Ads report timing', 'description': 'Can we change the daily report to run at 9 AM instead of 8 AM?', 'status': 'in_progress', 'priority': 'low'},
            {'client': clients[2], 'subject': 'Error workflow constantly alerting', 'description': 'The error monitoring workflow is sending too many alerts. Please adjust the threshold.', 'status': 'open', 'priority': 'high'},
        ]

        for ticket_data in tickets_data:
            ticket, created = SupportTicket.objects.get_or_create(
                client=ticket_data['client'],
                subject=ticket_data['subject'],
                defaults=ticket_data
            )
            if created:
                if ticket.status == 'resolved':
                    ticket.resolved_at = timezone.now() - timedelta(days=random.randint(1, 5))
                    ticket.save()
                self.stdout.write(f'Created ticket: {ticket.subject}')

        # Create sample client users
        users_data = [
            {'username': 'john_acme', 'email': 'john@acme-ecommerce.com', 'password': 'demo1234', 'client': clients[0]},
            {'username': 'sarah_digital', 'email': 'sarah@digitalmarketingpro.com', 'password': 'demo1234', 'client': clients[1]},
            {'username': 'mike_tech', 'email': 'mike@techstart.io', 'password': 'demo1234', 'client': clients[2]},
        ]

        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'is_staff': False,
                    'is_active': True
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'Created user: {user.username}')

            # Create client profile
            profile, profile_created = ClientProfile.objects.get_or_create(
                user=user,
                defaults={'client': user_data['client']}
            )
            if profile_created:
                self.stdout.write(f'Created profile for: {user.username}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\nSample data creation complete!'))
        self.stdout.write(f'- Clients: {Client.objects.count()}')
        self.stdout.write(f'- Workflows: {Workflow.objects.count()}')
        self.stdout.write(f'- Executions: {Execution.objects.count()}')
        self.stdout.write(f'- Invoices: {Invoice.objects.count()}')
        self.stdout.write(f'- Support Tickets: {SupportTicket.objects.count()}')
        self.stdout.write(f'- Users: {User.objects.filter(is_staff=False).count()}')
        self.stdout.write('\nTest user credentials:')
        for user_data in users_data:
            self.stdout.write(f'  Username: {user_data["username"]} | Password: {user_data["password"]}')
