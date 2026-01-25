"""
URL configuration for portal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from clients.admin_views import admin_dashboard
from clients import mcp_admin_views
from clients import execution_admin_views

urlpatterns = [
    # MCP Server management routes (MUST BE FIRST!)
    path('admin/mcp/', mcp_admin_views.mcp_dashboard, name='mcp_dashboard'),
    path('admin/mcp/workflows/', mcp_admin_views.mcp_workflows, name='mcp_workflows'),
    path('admin/mcp/workflows/<str:workflow_id>/<str:action>/',
         mcp_admin_views.mcp_workflow_action, name='mcp_workflow_action'),
    path('admin/mcp/api/health/', mcp_admin_views.mcp_health_check, name='mcp_health'),
    path('admin/mcp/api/stats/', mcp_admin_views.mcp_stats_api, name='mcp_stats'),

    # Execution monitoring routes
    path('admin/executions/', execution_admin_views.execution_dashboard, name='execution_dashboard'),
    path('admin/executions/<uuid:execution_id>/', execution_admin_views.execution_detail, name='execution_detail'),
    path('admin/executions/sync/', execution_admin_views.sync_executions_view, name='sync_executions'),
    path('admin/executions/api/stats/', execution_admin_views.execution_stats_api, name='execution_stats_api'),
    path('admin/executions/api/chart/', execution_admin_views.execution_chart_data_api, name='execution_chart_api'),

    # Django admin (MUST BE AFTER MCP/Execution routes!)
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
