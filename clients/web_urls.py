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
    path('logout/', auth_views.LogoutView.as_view(
        template_name='clients/logout_confirm.html',
        next_page='portal:login'
    ), name='logout'),

    # Client portal pages
    path('', web_views.dashboard_view, name='dashboard'),
    path('workflows/', web_views.workflows_view, name='workflows'),
    path('invoices/', web_views.invoices_view, name='invoices'),
    path('support/', web_views.support_view, name='support'),
    path('support/create/', web_views.create_support_ticket_view, name='create-ticket'),

    # Execution monitoring (client portal)
    path('executions/', web_views.executions_view, name='executions'),
    path('executions/<uuid:execution_id>/', web_views.execution_detail_view, name='execution-detail'),
    path('executions/api/stats/', web_views.execution_stats_api, name='execution-stats-api'),
]
