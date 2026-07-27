import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

import stripe
import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.billing_repository import BillingRepository
from app.services.eligibility_service import EligibilityService
from app.services.stripe_service import StripeInvoiceService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class InvoiceProcessResult:
    status: str
    reason: str
    organization_invoice_id: uuid.UUID | None = None
    stripe_invoice_id: str | None = None


class InvoiceProcessingService:
    def __init__(
        self,
        *,
        db: Session,
        stripe_service: StripeInvoiceService,
    ) -> None:
        self.db = db
        self.repository = BillingRepository(db)
        self.eligibility_service = EligibilityService()
        self.stripe_service = stripe_service

    def process(
        self,
        *,
        appointment_referral_id: uuid.UUID,
        trigger_source: str,
    ) -> InvoiceProcessResult:
        context = self.repository.get_context(appointment_referral_id)
        if context is None:
            return InvoiceProcessResult("skipped", "billing_context_not_found")

        eligibility = self.eligibility_service.evaluate(context)
        if not eligibility.eligible:
            status = (
                "already_processed"
                if eligibility.reason == "invoice_already_exists"
                else "skipped"
            )
            return InvoiceProcessResult(status, eligibility.reason)

        assert eligibility.amount is not None
        description = (
            f"Ultrasound service - ScanX appointment reference "
            f"{context.appointment.appointment_id}"
        )

        reserved_id = self.repository.reserve_invoice(
            appointment_referral_id=appointment_referral_id,
            appointment_id=context.appointment.appointment_id,
            organization_id=context.organization.id,
            amount=eligibility.amount,
            service_description=description,
            service_date=context.appointment.date,
        )

        if reserved_id is None:
            return InvoiceProcessResult("already_processed", "invoice_already_exists")

        amount_cents = int(
            (eligibility.amount * Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        idempotency_key = f"scanx-invoice-{appointment_referral_id}"

        try:
            stripe_result = self.stripe_service.create_and_send_invoice(
                context=context,
                amount_cents=amount_cents,
                description=description,
                idempotency_key=idempotency_key,
            )

            self.repository.mark_invoice_sent(
                organization_invoice_id=reserved_id,
                stripe_customer_id=stripe_result.customer_id,
                stripe_invoice_id=stripe_result.invoice_id,
                stripe_invoice_number=stripe_result.invoice_number,
                finalized_at=stripe_result.finalized_at,
                sent_at=stripe_result.sent_at,
                due_at=stripe_result.due_at,
            )

            logger.info(
                "invoice_sent",
                appointment_referral_id=str(appointment_referral_id),
                organization_invoice_id=str(reserved_id),
                stripe_invoice_id=stripe_result.invoice_id,
                trigger_source=trigger_source,
            )

            return InvoiceProcessResult(
                status="sent",
                reason="invoice_sent",
                organization_invoice_id=reserved_id,
                stripe_invoice_id=stripe_result.invoice_id,
            )

        except (stripe.error.APIConnectionError, stripe.error.RateLimitError) as exc:
            self.repository.mark_invoice_failed(reserved_id)
            logger.exception(
                "invoice_retryable_failure",
                appointment_referral_id=str(appointment_referral_id),
                organization_invoice_id=str(reserved_id),
            )
            return InvoiceProcessResult(
                status="retryable_failure",
                reason=type(exc).__name__,
                organization_invoice_id=reserved_id,
            )

        except (stripe.error.StripeError, SQLAlchemyError) as exc:
            self.repository.mark_invoice_failed(reserved_id)
            logger.exception(
                "invoice_processing_failed",
                appointment_referral_id=str(appointment_referral_id),
                organization_invoice_id=str(reserved_id),
            )
            return InvoiceProcessResult(
                status="failed",
                reason=type(exc).__name__,
                organization_invoice_id=reserved_id,
            )
