from dataclasses import dataclass
from datetime import datetime, timezone

import stripe

from app.core.config import settings
from app.repositories.billing_repository import BillingContext


@dataclass(frozen=True)
class StripeInvoiceResult:
    customer_id: str
    invoice_id: str
    invoice_number: str | None
    finalized_at: datetime | None
    sent_at: datetime
    due_at: datetime | None


class StripeInvoiceService:
    def __init__(self) -> None:
        stripe.api_key = settings.stripe_secret_key.get_secret_value()

    def _get_or_create_customer(self, context: BillingContext) -> str:
        organization = context.organization

        if organization.stripe_customer_id:
            return organization.stripe_customer_id

        customer = stripe.Customer.create(
            name=organization.display_name or organization.legal_name,
            email=context.billing_email,
            metadata={"scanx_organization_id": str(organization.id)},
            idempotency_key=f"scanx-customer-{organization.id}",
        )
        return customer["id"]

    def create_and_send_invoice(
        self,
        *,
        context: BillingContext,
        amount_cents: int,
        description: str,
        idempotency_key: str,
    ) -> StripeInvoiceResult:
        customer_id = self._get_or_create_customer(context)
        payment_terms_days = max(context.organization.payment_terms_days, 0)

        stripe.InvoiceItem.create(
            customer=customer_id,
            amount=amount_cents,
            currency=settings.stripe_default_currency,
            description=description,
            metadata={
                "scanx_appointment_id": context.appointment.appointment_id,
                "scanx_referral_id": str(context.referral.id),
            },
            idempotency_key=f"{idempotency_key}-item",
        )

        invoice_params = {
            "customer": customer_id,
            "collection_method": settings.stripe_invoice_collection_method,
            "auto_advance": False,
            "metadata": {
                "scanx_appointment_id": context.appointment.appointment_id,
                "scanx_referral_id": str(context.referral.id),
            },
        }

        if settings.stripe_invoice_collection_method == "send_invoice":
            invoice_params["days_until_due"] = payment_terms_days

        invoice = stripe.Invoice.create(
            **invoice_params,
            idempotency_key=f"{idempotency_key}-invoice",
        )

        finalized = stripe.Invoice.finalize_invoice(
            invoice["id"],
            idempotency_key=f"{idempotency_key}-finalize",
        )

        sent = finalized
        if settings.stripe_invoice_collection_method == "send_invoice":
            sent = stripe.Invoice.send_invoice(
                finalized["id"],
                idempotency_key=f"{idempotency_key}-send",
            )

        finalized_at = None
        transitions = sent.get("status_transitions") or {}
        if transitions.get("finalized_at"):
            finalized_at = datetime.fromtimestamp(
                transitions["finalized_at"], tz=timezone.utc
            )

        due_at = None
        if sent.get("due_date"):
            due_at = datetime.fromtimestamp(sent["due_date"], tz=timezone.utc)

        return StripeInvoiceResult(
            customer_id=customer_id,
            invoice_id=sent["id"],
            invoice_number=sent.get("number"),
            finalized_at=finalized_at,
            sent_at=datetime.now(timezone.utc),
            due_at=due_at,
        )
