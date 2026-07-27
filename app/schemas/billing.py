import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BillingScheduleRequest(BaseModel):
    appointment_referral_id: uuid.UUID

    trigger_source: Literal[
        "n8n_complete",
        "manual",
    ] = "n8n_complete"

    delay_seconds: int | None = Field(
        default=None,
        ge=0,
        le=86400,
        description=(
            "Optional delay override. When omitted, "
            "INVOICE_DELAY_SECONDS is used."
        ),
    )


class BillingScheduleResponse(BaseModel):
    status: Literal[
        "scheduled",
        "already_scheduled",
    ]

    appointment_referral_id: uuid.UUID
    task_name: str
    scheduled_for: datetime


class BillingProcessRequest(BaseModel):
    appointment_referral_id: uuid.UUID

    trigger_source: Literal[
        "primary",
        "nightly",
        "manual",
    ] = "primary"


class BillingProcessResponse(BaseModel):
    status: str
    reason: str

    appointment_referral_id: uuid.UUID

    organization_invoice_id: uuid.UUID | None = None
    stripe_invoice_id: str | None = None