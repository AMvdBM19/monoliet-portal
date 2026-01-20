"""
URL configuration for portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from clients.admin_views import admin_dashboard
from clients import mcp_admin_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # MCP Server management routes
    path('admin/mcp/', mcp_admin_views.mcp_dashboard, name='admin:mcp_dashboard'),
    path('admin/mcp/workflows/', mcp_admin_views.mcp_workflows, name='admin:mcp_workflows'),
    path('admin/mcp/workflows/<str:workflow_id>/<str:action>/',
         mcp_admin_views.mcp_workflow_action, name='admin:mcp_workflow_action'),
    path('admin/mcp/api/health/', mcp_admin_views.mcp_health_check, name='admin:mcp_health'),
    path('admin/mcp/api/stats/', mcp_admin_views.mcp_stats_api, name='admin:mcp_stats'),

    # Existing routes
    path('api/', include('clients.urls')),
    path('', include('clients.web_urls')),
]

# Override admin index with custom dashboard
admin.site.index_template = 'admin/index.html'
admin.site.index = admin_dashboard

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
