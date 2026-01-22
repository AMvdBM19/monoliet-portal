"""
URL configuration for portal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from clients.admin_views import admin_dashboard
from clients import mcp_admin_views

urlpatterns = [
    # MCP Server management routes (MUST BE FIRST!)
    path('admin/mcp/', mcp_admin_views.mcp_dashboard, name='mcp_dashboard'),
    path('admin/mcp/workflows/', mcp_admin_views.mcp_workflows, name='mcp_workflows'),
    path('admin/mcp/workflows/<str:workflow_id>/<str:action>/',
         mcp_admin_views.mcp_workflow_action, name='mcp_workflow_action'),
    path('admin/mcp/api/health/', mcp_admin_views.mcp_health_check, name='mcp_health'),
    path('admin/mcp/api/stats/', mcp_admin_views.mcp_stats_api, name='mcp_stats'),
    
    # Django admin (MUST BE AFTER MCP routes!)
    path('admin/', admin.site.urls),
    
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
