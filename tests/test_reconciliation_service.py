import uuid
from unittest.mock import Mock
from datetime import datetime, timezone
from app.schemas.reconciliation import (
    ReconciliationCandidate,
    ReconciliationRequest,
)
from app.services.reconciliation_service import (
    ReconciliationService,
)
from app.services.task_service import (
    TaskScheduleResult,
)

def test_dry_run_does_not_schedule_tasks(db_session):
    task_service = Mock()

    service = ReconciliationService(
        db=db_session,
        task_service=task_service,
    )

    referral_id = uuid.uuid4()

    service.repository.find_missing_invoice_candidates = (
        Mock(
            return_value=[
                ReconciliationCandidate(
                    appointment_referral_id=(
                        referral_id
                    ),
                    appointment_id=123,
                    organization_id=uuid.uuid4(),
                )
            ]
        )
    )

    response = service.reconcile(
        ReconciliationRequest(
            dry_run=True,
        )
    )

    assert response.candidates_found == 1
    assert response.tasks_scheduled == 0
    assert response.tasks_already_scheduled == 0

    task_service.schedule_invoice.assert_not_called()

def test_reconciliation_schedules_task(db_session):
    task_service = Mock()

    service = ReconciliationService(
        db=db_session,
        task_service=task_service,
    )

    referral_id = uuid.uuid4()

    service.repository.find_missing_invoice_candidates = (
        Mock(
            return_value=[
                ReconciliationCandidate(
                    appointment_referral_id=(
                        referral_id
                    ),
                    appointment_id=123,
                    organization_id=uuid.uuid4(),
                )
            ]
        )
    )

    task_service.schedule_invoice.return_value = (
        TaskScheduleResult(
            status="scheduled",
            task_name=(
                "projects/test/locations/test/"
                "queues/test/tasks/test"
            ),
            scheduled_for=(
                __import__("datetime")
                .datetime.now(
                    __import__("datetime")
                    .timezone.utc
                )
            ),
        )
    )

    response = service.reconcile(
        ReconciliationRequest()
    )

    assert response.candidates_found == 1
    assert response.tasks_scheduled == 1
    assert response.tasks_already_scheduled == 0
    assert response.failures == 0

    task_service.schedule_invoice.assert_called_once()

def test_reconciliation_counts_duplicate_task(db_session):
    task_service = Mock()

    service = ReconciliationService(
        db=db_session,
        task_service=task_service,
    )

    referral_id = uuid.uuid4()

    service.repository.find_missing_invoice_candidates = (
        Mock(
            return_value=[
                ReconciliationCandidate(
                    appointment_referral_id=(
                        referral_id
                    ),
                    appointment_id=123,
                    organization_id=uuid.uuid4(),
                )
            ]
        )
    )

    task_service.schedule_invoice.return_value = (
        TaskScheduleResult(
            status="already_scheduled",
            task_name=(
                "projects/test/locations/test/"
                "queues/test/tasks/test"
            ),
            scheduled_for=(
                datetime.now(timezone.utc)
            ),
        )
    )

    response = service.reconcile(
        ReconciliationRequest()
    )

    assert response.tasks_scheduled == 0
    assert response.tasks_already_scheduled == 1
    assert response.failures == 0