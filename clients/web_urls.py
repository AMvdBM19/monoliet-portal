"""
Web URL routing for the Monoliet Client Portal.

This module defines URL patterns for the web-based client portal views.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import web_views

app_name = 'portal'

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='clients/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='portal:login'), name='logout'),

    # Client portal pages
    path('', web_views.dashboard_view, name='dashboard'),
    path('workflows/', web_views.workflows_view, name='workflows'),
    path('invoices/', web_views.invoices_view, name='invoices'),
    path('support/', web_views.support_view, name='support'),
    path('support/create/', web_views.create_support_ticket_view, name='create-ticket'),
]
