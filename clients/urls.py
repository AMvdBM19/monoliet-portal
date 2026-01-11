"""
API URL routing for the Monoliet Client Portal.

This module defines all API endpoints using Django REST Framework's router.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, WorkflowViewSet, APICredentialViewSet,
    ExecutionViewSet, InvoiceViewSet, SupportTicketViewSet,
    CustomAuthToken, logout_view
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'credentials', APICredentialViewSet, basename='apicredential')
router.register(r'executions', ExecutionViewSet, basename='execution')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'support-tickets', SupportTicketViewSet, basename='supportticket')

# API URL patterns
urlpatterns = [
    # Authentication endpoints
    path('auth/token/', CustomAuthToken.as_view(), name='api-token-auth'),
    path('auth/logout/', logout_view, name='api-logout'),

    # Include router URLs
    path('', include(router.urls)),
]
