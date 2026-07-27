from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReconciliationRequest(BaseModel):
    lookback_days: int | None = Field(
        default=None,
        ge=1,
        le=90,
    )

    batch_size: int | None = Field(
        default=None,
        ge=1,
        le=1000,
    )

    dry_run: bool = False


class ReconciliationCandidate(BaseModel):
    appointment_referral_id: UUID
    appointment_id: int
    organization_id: UUID


class ReconciliationFailure(BaseModel):
    appointment_referral_id: UUID
    reason: str


class ReconciliationResponse(BaseModel):
    started_at: datetime
    completed_at: datetime

    lookback_days: int
    batch_size: int
    dry_run: bool

    candidates_found: int
    tasks_scheduled: int
    tasks_already_scheduled: int
    failures: int

    candidate_ids: list[UUID]
    failed_items: list[ReconciliationFailure]