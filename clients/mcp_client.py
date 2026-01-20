"""
MCP Server Management API Client.

Provides Python interface to the MCP server's management REST API.
Handles authentication, error handling, and response parsing.
"""

import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for interacting with MCP Server Management API.

    Designed to be used from Django admin views to manage
    the MCP server remotely.
    """

    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        """
        Initialize MCP client.

        Args:
            base_url: MCP Management API base URL (e.g., http://localhost:8002)
            auth_token: Optional auth token. If None, will try to use Django admin user token.
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.timeout = 10.0

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        return headers

    async def health_check(self) -> Dict[str, Any]:
        """
        Check MCP server health.

        Returns:
            dict: Health status
            {
                "healthy": bool,
                "n8n_reachable": bool,
                "database_connected": bool,
                "errors": List[str]
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"MCP health check failed: {e}")
                return {
                    "healthy": False,
                    "n8n_reachable": False,
                    "database_connected": False,
                    "errors": [str(e)]
                }

    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive MCP server status.

        Returns:
            dict: Server status including uptime, connectivity, ports, etc.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/status",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def get_workflow_stats(self) -> Dict[str, Any]:
        """
        Get aggregated workflow statistics.

        Returns:
            dict: Workflow stats
            {
                "total_workflows": int,
                "active_workflows": int,
                "paused_workflows": int,
                "error_workflows": int,
                "total_executions_today": int,
                "success_rate": float
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/workflows/stats",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def list_workflows(
        self,
        active_only: bool = False,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List workflows with optional filtering.

        Args:
            active_only: Only return active workflows
            search: Search term for workflow names

        Returns:
            dict: {"workflows": List[dict], "count": int}
        """
        params = {}
        if active_only:
            params["active_only"] = "true"
        if search:
            params["search"] = search

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/workflows",
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a workflow."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/activate",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Deactivate a workflow."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/deactivate",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Manually trigger workflow execution."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/workflows/{workflow_id}/execute",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def get_config(self) -> Dict[str, Any]:
        """Get MCP server configuration (redacted)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/config",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()


def get_mcp_client() -> Optional[MCPClient]:
    """
    Factory function to create MCP client from PortalSettings.

    Returns:
        MCPClient instance if MCP server is enabled, None otherwise.
    """
    from .models import PortalSettings

    try:
        settings = PortalSettings.objects.first()
        if not settings or not settings.mcp_server_enabled:
            return None

        return MCPClient(
            base_url=settings.mcp_server_url,
            auth_token=settings.mcp_server_auth_token or None
        )
    except Exception as e:
        logger.error(f"Failed to create MCP client: {e}")
        return None
