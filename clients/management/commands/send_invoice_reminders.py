"""
Management command to send invoice payment reminders.

Sends email reminders for invoices that are:
- Due in 3 days (warning)
- Due today (urgent)
- Overdue (past due)

This command should be run daily via cron.

Usage:
    python manage.py send_invoice_reminders
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
from clients.models import Invoice


class Command(BaseCommand):
    help = 'Send email reminders for upcoming and overdue invoices'

    def handle(self, *args, **options):
        self.stdout.write('Checking for invoices requiring reminders...')

        today = date.today()
        three_days_from_now = today + timedelta(days=3)

        # Get pending invoices
        pending_invoices = Invoice.objects.filter(status='pending')

        sent_count = 0
        error_count = 0

        for invoice in pending_invoices:
            try:
                # Determine reminder type
                reminder_type = None
                subject_prefix = ''

                if invoice.due_date < today:
                    # Overdue
                    reminder_type = 'overdue'
                    subject_prefix = 'OVERDUE: '
                    days_overdue = (today - invoice.due_date).days
                    urgency_message = f'This invoice is {days_overdue} day(s) overdue.'
                elif invoice.due_date == today:
                    # Due today
                    reminder_type = 'due_today'
                    subject_prefix = 'DUE TODAY: '
                    urgency_message = 'This invoice is due today.'
                elif invoice.due_date <= three_days_from_now:
                    # Due in 3 days or less
                    reminder_type = 'upcoming'
                    subject_prefix = 'REMINDER: '
                    days_until_due = (invoice.due_date - today).days
                    urgency_message = f'This invoice is due in {days_until_due} day(s).'
                else:
                    # Not due for reminder yet
                    continue

                # Send email reminder
                send_mail(
                    subject=f'{subject_prefix}Invoice {invoice.invoice_number} Payment Reminder',
                    message=f'''Dear {invoice.client.contact_name},

{urgency_message}

Invoice Details:
- Invoice Number: {invoice.invoice_number}
- Amount: ${invoice.amount}
- Due Date: {invoice.due_date.strftime('%B %d, %Y')}
- Type: {invoice.get_type_display()}

Please ensure payment is processed as soon as possible to avoid any service interruptions.

If you have already made this payment, please disregard this reminder.

You can view this invoice in your client portal at: https://{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'portal.monoliet.cloud'}

If you have any questions, please contact us.

Best regards,
The Monoliet Team
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[invoice.client.email],
                    fail_silently=False,
                )

                sent_count += 1
                self.stdout.write(f'Sent {reminder_type} reminder for invoice {invoice.invoice_number} to {invoice.client.email}')

                # Update overdue status
                if reminder_type == 'overdue' and invoice.status == 'pending':
                    invoice.status = 'overdue'
                    invoice.save()
                    self.stdout.write(f'  Updated invoice {invoice.invoice_number} status to overdue')

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(
                    f'Error sending reminder for invoice {invoice.invoice_number}: {str(e)}'
                ))
                continue

        self.stdout.write(self.style.SUCCESS(
            f'Reminder sending complete! Sent {sent_count} reminders. Errors: {error_count}'
        ))
