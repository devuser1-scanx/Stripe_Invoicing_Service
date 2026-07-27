import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.reconciliation_repository import (
    ReconciliationRepository,
)
from app.schemas.reconciliation import (
    ReconciliationFailure,
    ReconciliationRequest,
    ReconciliationResponse,
)
from app.services.task_service import CloudTaskService


logger = logging.getLogger(__name__)


class ReconciliationService:
    def __init__(
        self,
        db: Session,
        task_service: CloudTaskService | None = None,
    ) -> None:
        self.repository = ReconciliationRepository(db)
        self.task_service = (
            task_service or CloudTaskService()
        )

    def reconcile(
        self,
        request: ReconciliationRequest,
    ) -> ReconciliationResponse:
        started_at = datetime.now(timezone.utc)

        lookback_days = (
            request.lookback_days
            if request.lookback_days is not None
            else settings.reconciliation_lookback_days
        )

        batch_size = (
            request.batch_size
            if request.batch_size is not None
            else settings.reconciliation_batch_size
        )

        candidates = (
            self.repository.find_missing_invoice_candidates(
                lookback_days=lookback_days,
                batch_size=batch_size,
            )
        )

        logger.info(
            "Nightly reconciliation found %s candidate(s). "
            "lookback_days=%s batch_size=%s dry_run=%s",
            len(candidates),
            lookback_days,
            batch_size,
            request.dry_run,
        )

        tasks_scheduled = 0
        tasks_already_scheduled = 0

        failed_items: list[
            ReconciliationFailure
        ] = []

        reconciliation_date = (
            started_at.strftime("%Y%m%d")
        )

        task_suffix = (
            f"reconcile-{reconciliation_date}"
        )

        for candidate in candidates:
            if request.dry_run:
                continue

            try:
                result = (
                    self.task_service.schedule_invoice(
                        appointment_referral_id=(
                            candidate
                            .appointment_referral_id
                        ),
                        trigger_source=(
                            "nightly"
                        ),
                        delay_seconds=(
                            settings
                            .reconciliation_task_delay_seconds
                        ),
                        task_suffix=task_suffix,
                    )
                )

                if result.status == "scheduled":
                    tasks_scheduled += 1

                elif (
                    result.status
                    == "already_scheduled"
                ):
                    tasks_already_scheduled += 1

                else:
                    failed_items.append(
                        ReconciliationFailure(
                            appointment_referral_id=(
                                candidate
                                .appointment_referral_id
                            ),
                            reason=(
                                "Unexpected Cloud Tasks "
                                f"status: {result.status}"
                            ),
                        )
                    )

            except Exception as exc:
                logger.exception(
                    "Failed to schedule reconciliation "
                    "task for appointment_referral_id=%s",
                    candidate.appointment_referral_id,
                )

                failed_items.append(
                    ReconciliationFailure(
                        appointment_referral_id=(
                            candidate
                            .appointment_referral_id
                        ),
                        reason=str(exc),
                    )
                )

        completed_at = datetime.now(timezone.utc)

        logger.info(
            "Nightly reconciliation completed. "
            "candidates=%s scheduled=%s "
            "already_scheduled=%s failures=%s",
            len(candidates),
            tasks_scheduled,
            tasks_already_scheduled,
            len(failed_items),
        )

        return ReconciliationResponse(
            started_at=started_at,
            completed_at=completed_at,
            lookback_days=lookback_days,
            batch_size=batch_size,
            dry_run=request.dry_run,
            candidates_found=len(candidates),
            tasks_scheduled=tasks_scheduled,
            tasks_already_scheduled=(
                tasks_already_scheduled
            ),
            failures=len(failed_items),
            candidate_ids=[
                candidate.appointment_referral_id
                for candidate in candidates
            ],
            failed_items=failed_items,
        )