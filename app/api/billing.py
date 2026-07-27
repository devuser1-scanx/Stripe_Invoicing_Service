from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.billing import (
    BillingProcessRequest,
    BillingProcessResponse,
    BillingScheduleRequest,
    BillingScheduleResponse,
)
from app.services.invoice_service import (
    InvoiceProcessingService,
)
from app.services.stripe_service import StripeInvoiceService
from app.services.task_service import CloudTaskService

from app.schemas.reconciliation import (
    ReconciliationRequest,
    ReconciliationResponse,
)
from app.services.reconciliation_service import (
    ReconciliationService,
)

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
)


@router.post(
    "/schedule",
    response_model=BillingScheduleResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def schedule_invoice(
    payload: BillingScheduleRequest,
) -> BillingScheduleResponse:
    """
    Called by n8n when a referral appointment changes to Complete.

    This endpoint does not create an invoice. It creates a Cloud Task that
    calls /billing/process after the configured delay.
    """

    task_service = CloudTaskService()

    result = task_service.schedule_invoice(
        appointment_referral_id=(
            payload.appointment_referral_id
        ),
        trigger_source="primary",
        delay_seconds=payload.delay_seconds,
    )

    return BillingScheduleResponse(
        status=result.status,
        appointment_referral_id=(
            payload.appointment_referral_id
        ),
        task_name=result.task_name,
        scheduled_for=result.scheduled_for,
    )


@router.post(
    "/process",
    response_model=BillingProcessResponse,
    status_code=status.HTTP_200_OK,
)
def process_invoice(
    payload: BillingProcessRequest,
    db: Session = Depends(get_db),
) -> BillingProcessResponse:
    """
    Called by Cloud Tasks.

    Rechecks eligibility and performs the actual Stripe invoice operation.
    """

    service = InvoiceProcessingService(
        db=db,
        stripe_service=StripeInvoiceService(),
    )

    result = service.process(
        appointment_referral_id=(
            payload.appointment_referral_id
        ),
        trigger_source=payload.trigger_source,
    )

    if result.status == "retryable_failure":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.reason,
        )

    return BillingProcessResponse(
        status=result.status,
        reason=result.reason,
        appointment_referral_id=(
            payload.appointment_referral_id
        ),
        organization_invoice_id=(
            result.organization_invoice_id
        ),
        stripe_invoice_id=result.stripe_invoice_id,
    )

# Reconciliation API
@router.post(
    "/reconcile",
    response_model=ReconciliationResponse,
)
def reconcile_invoices(
    request: ReconciliationRequest,
    db: Session = Depends(get_db),
) -> ReconciliationResponse:
    service = ReconciliationService(db)

    return service.reconcile(request)