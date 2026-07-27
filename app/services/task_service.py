import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from google.api_core.exceptions import AlreadyExists
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from app.core.config import settings


@dataclass(frozen=True)
class TaskScheduleResult:
    status: str
    task_name: str
    scheduled_for: datetime


class CloudTaskService:
    def __init__(
        self,
        client: tasks_v2.CloudTasksClient | None = None,
    ) -> None:
        self.client = client or tasks_v2.CloudTasksClient()

        self.queue_path = self.client.queue_path(
            settings.gcp_project_id,
            settings.gcp_region,
            settings.cloud_tasks_queue,
        )

    @staticmethod
    def _sanitize_task_id(value: str) -> str:
        """
        Cloud Tasks task IDs should contain only safe characters.

        UUIDs are already safe, but sanitizing prevents errors when suffixes
        are added later for nightly reconciliation.
        """
        cleaned = re.sub(
            pattern=r"[^A-Za-z0-9_-]",
            repl="-",
            string=value,
        )

        return cleaned[:500]

    def schedule_invoice(
        self,
        *,
        appointment_referral_id: uuid.UUID,
        trigger_source: str,
        delay_seconds: int | None = None,
        task_suffix: str | None = None,
    ) -> TaskScheduleResult:
        actual_delay = (
            settings.invoice_delay_seconds
            if delay_seconds is None
            else delay_seconds
        )

        scheduled_for = (
            datetime.now(timezone.utc)
            + timedelta(seconds=actual_delay)
        )

        suffix = (
            f"-{task_suffix}"
            if task_suffix
            else ""
        )

        task_id = self._sanitize_task_id(
            f"invoice-{appointment_referral_id}{suffix}"
        )

        full_task_name = self.client.task_path(
            settings.gcp_project_id,
            settings.gcp_region,
            settings.cloud_tasks_queue,
            task_id,
        )

        schedule_timestamp = timestamp_pb2.Timestamp()
        schedule_timestamp.FromDatetime(scheduled_for)

        payload = {
            "appointment_referral_id": str(
                appointment_referral_id
            ),
            "trigger_source": trigger_source,
        }

        task = tasks_v2.Task(
            name=full_task_name,
            schedule_time=schedule_timestamp,
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=(
                    f"{settings.billing_service_url.rstrip('/')}"
                    "/billing/process"
                ),
                headers={
                    "Content-Type": "application/json",
                },
                body=json.dumps(payload).encode("utf-8"),
                oidc_token=tasks_v2.OidcToken(
                    service_account_email=(
                        settings
                        .cloud_tasks_invoker_service_account
                    ),
                    audience=settings.billing_service_url,
                ),
            ),
        )

        try:
            created_task = self.client.create_task(
                request=tasks_v2.CreateTaskRequest(
                    parent=self.queue_path,
                    task=task,
                )
            )

            return TaskScheduleResult(
                status="scheduled",
                task_name=created_task.name,
                scheduled_for=scheduled_for,
            )

        except AlreadyExists:
            # Duplicate n8n webhook or repeated scheduling attempt.
            # Treat this as successful and do not create another task.
            return TaskScheduleResult(
                status="already_scheduled",
                task_name=full_task_name,
                scheduled_for=scheduled_for,
            )