"""
Django forms for the Monoliet Client Portal.

This module provides forms for client-facing web interface.
"""

from django import forms
from .models import SupportTicket


class SupportTicketForm(forms.ModelForm):
    """
    Form for creating support tickets.

    Used by clients to submit support requests through the web interface.
    """

    class Meta:
        model = SupportTicket
        fields = ['subject', 'description', 'priority']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Enter a brief subject line'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 6,
                'placeholder': 'Describe your issue in detail'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
        }
        labels = {
            'subject': 'Subject',
            'description': 'Description',
            'priority': 'Priority Level',
        }
        help_texts = {
            'priority': 'Select the urgency level for this ticket',
        }
