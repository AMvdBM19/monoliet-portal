"""
Execution synchronization service.

Syncs n8n execution data to Django Execution model.
Handles incremental updates and data mapping.
"""

from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from .models import Execution, Workflow, Client
from .utils import get_n8n_client

logger = logging.getLogger(__name__)


class ExecutionSyncService:
    """
    Service for syncing n8n executions to Django database.

    Fetches execution data from n8n API and updates the local
    Execution model with aggregated daily statistics.
    """

    # Map n8n statuses to normalized values
    STATUS_MAP = {
        'success': 'success',
        'error': 'error',
        'running': 'running',
        'waiting': 'waiting',
        'canceled': 'canceled',
        'crashed': 'error',
        'new': 'running',
        'unknown': 'error'
    }

    def __init__(self):
        """Initialize the sync service with n8n client."""
        self.n8n_client = get_n8n_client()

    def sync_all_executions(self, limit: int = 100) -> Dict[str, int]:
        """
        Sync recent executions for all workflows.

        Fetches the most recent executions from n8n and updates
        the corresponding Execution records in the database.

        Args:
            limit: Max executions to fetch per request (max 250)

        Returns:
            dict: {"created": N, "updated": N, "errors": N, "skipped": N}
        """
        stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}

        try:
            logger.info(f"Starting execution sync with limit={limit}")

            # Fetch recent executions from n8n
            response = self.n8n_client.get_executions(
                limit=min(limit, 250),
                include_data=False
            )

            executions = response.get('data', [])
            logger.info(f"Fetched {len(executions)} executions from n8n API")

            if not executions:
                logger.warning("No executions returned from n8n API")
                return stats

            # Log sample execution for debugging
            if executions:
                sample = executions[0]
                logger.debug(
                    f"Sample execution: id={sample.get('id')}, "
                    f"workflowId={sample.get('workflowId')}, "
                    f"status={sample.get('status')}, "
                    f"startedAt={sample.get('startedAt')}"
                )

            # Process executions by workflow and date
            execution_groups = self._group_executions_by_workflow_date(executions)
            logger.info(f"Grouped into {len(execution_groups)} workflow/date combinations")

            for (workflow_id, exec_date), exec_list in execution_groups.items():
                try:
                    result = self._sync_execution_group(workflow_id, exec_date, exec_list)
                    stats[result] += 1
                except Exception as e:
                    logger.error(
                        f"Failed to sync execution group {workflow_id}/{exec_date}: {e}",
                        exc_info=True
                    )
                    stats['errors'] += 1

            logger.info(f"Execution sync complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Execution sync failed: {e}", exc_info=True)
            stats['errors'] += 1
            return stats

    def sync_workflow_executions(
        self,
        workflow_id: str,
        limit: int = 50
    ) -> Dict[str, int]:
        """
        Sync executions for a specific workflow.

        Args:
            workflow_id: n8n workflow ID
            limit: Max executions to fetch

        Returns:
            dict: Sync statistics
        """
        stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}

        try:
            logger.info(f"Syncing executions for workflow {workflow_id} with limit={limit}")

            executions = self.n8n_client.get_workflow_executions(
                workflow_id=workflow_id,
                limit=limit
            )

            logger.info(f"Fetched {len(executions)} executions for workflow {workflow_id}")

            if not executions:
                logger.warning(f"No executions found for workflow {workflow_id}")
                return stats

            # Group by date
            execution_groups = self._group_executions_by_workflow_date(executions)
            logger.info(f"Grouped into {len(execution_groups)} date combinations")

            for (wf_id, exec_date), exec_list in execution_groups.items():
                try:
                    result = self._sync_execution_group(wf_id, exec_date, exec_list)
                    stats[result] += 1
                except Exception as e:
                    logger.error(
                        f"Failed to sync execution group {wf_id}/{exec_date}: {e}",
                        exc_info=True
                    )
                    stats['errors'] += 1

            logger.info(f"Workflow sync complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Workflow execution sync failed: {e}", exc_info=True)
            stats['errors'] += 1
            return stats

    def _group_executions_by_workflow_date(
        self,
        executions: List[Dict]
    ) -> Dict[tuple, List[Dict]]:
        """
        Group executions by workflow ID and date.

        Args:
            executions: List of execution data from n8n

        Returns:
            Dict mapping (workflow_id, date) tuples to execution lists
        """
        groups = {}
        skipped_no_workflow = 0
        skipped_no_date = 0

        for exec_data in executions:
            workflow_id = str(exec_data.get('workflowId', ''))
            started_at = self._parse_datetime(exec_data.get('startedAt'))

            if not workflow_id:
                skipped_no_workflow += 1
                continue

            if not started_at:
                # Try stoppedAt as fallback
                started_at = self._parse_datetime(exec_data.get('stoppedAt'))
                if not started_at:
                    skipped_no_date += 1
                    continue

            exec_date = started_at.date()
            key = (workflow_id, exec_date)

            if key not in groups:
                groups[key] = []
            groups[key].append(exec_data)

        if skipped_no_workflow > 0:
            logger.warning(f"Skipped {skipped_no_workflow} executions with no workflow ID")
        if skipped_no_date > 0:
            logger.warning(f"Skipped {skipped_no_date} executions with no valid date")

        return groups

    def _sync_execution_group(
        self,
        workflow_id: str,
        exec_date,
        executions: List[Dict]
    ) -> str:
        """
        Sync a group of executions for a workflow on a specific date.

        Args:
            workflow_id: n8n workflow ID
            exec_date: Date of executions
            executions: List of execution data

        Returns:
            str: 'created', 'updated', or 'skipped'
        """
        logger.debug(
            f"Processing {len(executions)} executions for workflow {workflow_id} on {exec_date}"
        )

        # Find corresponding Django workflow
        try:
            workflow = Workflow.objects.get(n8n_workflow_id=workflow_id)
        except Workflow.DoesNotExist:
            logger.warning(
                f"Workflow {workflow_id} not found in database. "
                f"Create a Workflow record with n8n_workflow_id='{workflow_id}' to track its executions."
            )
            return 'skipped'

        # Calculate statistics for this group
        total_count = len(executions)
        success_count = sum(
            1 for e in executions
            if self._map_status(e.get('status')) == 'success'
        )
        error_count = sum(
            1 for e in executions
            if self._map_status(e.get('status')) == 'error'
        )

        logger.debug(
            f"Stats for {workflow_id}/{exec_date}: "
            f"total={total_count}, success={success_count}, error={error_count}"
        )

        # Update or create execution record
        with transaction.atomic():
            execution, created = Execution.objects.update_or_create(
                workflow=workflow,
                execution_date=exec_date,
                defaults={
                    'client': workflow.client,
                    'total_count': total_count,
                    'success_count': success_count,
                    'error_count': error_count,
                }
            )

        action = 'Created' if created else 'Updated'
        logger.debug(f"{action} execution record {execution.id} for {workflow_id}/{exec_date}")

        return 'created' if created else 'updated'

    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """
        Parse ISO datetime string from n8n API.

        Args:
            dt_string: ISO format datetime string

        Returns:
            datetime object or None if parsing fails
        """
        if not dt_string:
            return None
        try:
            # Handle both Z suffix and timezone offset
            if dt_string.endswith('Z'):
                dt_string = dt_string[:-1] + '+00:00'
            return datetime.fromisoformat(dt_string)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse datetime '{dt_string}': {e}")
            return None

    def _map_status(self, n8n_status: str) -> str:
        """
        Map n8n execution status to normalized value.

        Args:
            n8n_status: Status string from n8n API

        Returns:
            Normalized status string
        """
        if not n8n_status:
            return 'error'
        return self.STATUS_MAP.get(n8n_status, 'error')


def sync_executions_for_workflow(workflow_id: str, limit: int = 50) -> Dict[str, int]:
    """
    Convenience function to sync executions for a workflow.

    Args:
        workflow_id: n8n workflow ID
        limit: Max executions to fetch

    Returns:
        dict: Sync statistics
    """
    service = ExecutionSyncService()
    return service.sync_workflow_executions(workflow_id, limit)


def sync_all_recent_executions(limit: int = 100) -> Dict[str, int]:
    """
    Convenience function to sync all recent executions.

    Args:
        limit: Max executions to fetch

    Returns:
        dict: Sync statistics
    """
    service = ExecutionSyncService()
    return service.sync_all_executions(limit)
