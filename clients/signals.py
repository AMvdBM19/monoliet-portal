"""
Django signals for the Monoliet Client Portal.

This module handles automatic email notifications when certain events occur.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import SupportTicket, Invoice, Workflow


@receiver(post_save, sender=SupportTicket)
def send_support_ticket_emails(sender, instance, created, **kwargs):
    """
    Send email notifications when a support ticket is created or updated.

    When created:
    - Email to client: Confirmation that ticket was received
    - Email to admin: Notification of new ticket

    When updated to resolved:
    - Email to client: Notification that ticket is resolved
    """
    if created:
        # Send confirmation email to client
        try:
            send_mail(
                subject=f'Support Ticket Created: {instance.subject}',
                message=f'''Dear {instance.client.contact_name},

We have received your support ticket.

Ticket ID: {instance.id}
Subject: {instance.subject}
Priority: {instance.get_priority_display()}
Status: {instance.get_status_display()}

Our team will review your request and respond as soon as possible.

Best regards,
The Monoliet Team
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.client.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send client email for ticket {instance.id}: {str(e)}")

        # Send notification email to admin
        try:
            send_mail(
                subject=f'New Support Ticket from {instance.client.company_name}',
                message=f'''A new support ticket has been created.

Client: {instance.client.company_name}
Contact: {instance.client.contact_name}
Email: {instance.client.email}

Ticket ID: {instance.id}
Subject: {instance.subject}
Priority: {instance.get_priority_display()}

Description:
{instance.description}

View in admin panel: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}/admin/clients/supportticket/{instance.id}/
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.EMAIL_HOST_USER],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send admin email for ticket {instance.id}: {str(e)}")

    else:
        # Check if status changed to resolved
        try:
            old_instance = SupportTicket.objects.get(pk=instance.pk)
            if old_instance.status != 'resolved' and instance.status == 'resolved':
                # Send resolution email to client
                send_mail(
                    subject=f'Support Ticket Resolved: {instance.subject}',
                    message=f'''Dear {instance.client.contact_name},

Your support ticket has been resolved.

Ticket ID: {instance.id}
Subject: {instance.subject}

If you have any further questions or concerns, please don't hesitate to create a new support ticket.

Best regards,
The Monoliet Team
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.client.email],
                    fail_silently=True,
                )
        except SupportTicket.DoesNotExist:
            pass
        except Exception as e:
            print(f"Failed to send resolution email for ticket {instance.id}: {str(e)}")


@receiver(post_save, sender=Invoice)
def send_invoice_email(sender, instance, created, **kwargs):
    """
    Send email notification when an invoice is created.

    Email to client with invoice details and payment information.
    """
    if created:
        try:
            send_mail(
                subject=f'New Invoice: {instance.invoice_number}',
                message=f'''Dear {instance.client.contact_name},

A new invoice has been generated for your account.

Invoice Number: {instance.invoice_number}
Amount: ${instance.amount}
Type: {instance.get_type_display()}
Due Date: {instance.due_date.strftime('%B %d, %Y')}

Please ensure payment is received by the due date to avoid any service interruptions.

You can view this invoice in your client portal.

Best regards,
The Monoliet Team
''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.client.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Failed to send invoice email for {instance.invoice_number}: {str(e)}")


@receiver(post_save, sender=Workflow)
def send_workflow_error_notification(sender, instance, created, **kwargs):
    """
    Send email notification when a workflow enters error state.

    Only sends email if the workflow status changed to 'error'.
    """
    if not created:
        try:
            # Get the previous state
            old_instance = Workflow.objects.get(pk=instance.pk)
            if old_instance.status != 'error' and instance.status == 'error':
                # Workflow just entered error state
                send_mail(
                    subject=f'Workflow Error Alert: {instance.workflow_name}',
                    message=f'''Alert: A workflow has entered an error state.

Client: {instance.client.company_name}
Workflow: {instance.workflow_name}
n8n Workflow ID: {instance.n8n_workflow_id}

Please investigate the issue in the n8n instance:
{settings.N8N_URL}/workflow/{instance.n8n_workflow_id}

Admin panel: {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'}/admin/clients/workflow/{instance.id}/
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.EMAIL_HOST_USER],
                    fail_silently=True,
                )
        except Workflow.DoesNotExist:
            pass
        except Exception as e:
            print(f"Failed to send workflow error email for {instance.workflow_name}: {str(e)}")


@receiver(pre_save, sender=Invoice)
def generate_invoice_number(sender, instance, **kwargs):
    """
    Automatically generate invoice number if not set.
    """
    if not instance.invoice_number:
        from .utils import generate_invoice_number
        instance.invoice_number = generate_invoice_number()


@receiver(post_save, sender=Invoice)
def mark_overdue_invoices(sender, instance, **kwargs):
    """
    Update invoice status to overdue if past due date.

    This is a backup signal; a management command should handle this in bulk.
    """
    from datetime import date

    if instance.status == 'pending' and instance.due_date < date.today():
        Invoice.objects.filter(pk=instance.pk).update(status='overdue')
