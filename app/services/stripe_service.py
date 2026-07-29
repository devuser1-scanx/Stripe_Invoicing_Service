from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

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
    """
    Creates or reuses a Stripe customer, creates a draft invoice,
    attaches the appointment charge directly to that invoice,
    finalizes it, and sends it to the organization's billing email.
    """

    def __init__(self) -> None:
        stripe.api_key = (
            settings.stripe_secret_key.get_secret_value()
        )

    @staticmethod
    def _timestamp_to_datetime(
        value: int | None,
    ) -> datetime | None:
        if not value:
            return None

        return datetime.fromtimestamp(
            value,
            tz=timezone.utc,
        )

    @staticmethod
    def _organization_name(
        context: BillingContext,
    ) -> str:
        organization = context.organization

        return (
            organization.display_name
            or organization.legal_name
        )

    @staticmethod
    def _metadata(
        context: BillingContext,
    ) -> dict[str, str]:
        return {
            "scanx_appointment_id": str(
                context.appointment.appointment_id
            ),
            "scanx_referral_id": str(
                context.referral.id
            ),
            "scanx_organization_id": str(
                context.organization.id
            ),
            "scanx_source": "organization_billing",
        }

    def _get_or_create_customer(
        self,
        context: BillingContext,
    ) -> str:
        organization = context.organization
        billing_email = context.billing_email

        if not billing_email:
            raise ValueError(
                "Organization billing email is missing."
            )

        customer_name = self._organization_name(
            context
        )

        customer_metadata = {
            "scanx_organization_id": str(
                organization.id
            ),
            "scanx_source": "referral_organization",
        }

        if organization.stripe_customer_id:
            customer = stripe.Customer.modify(
                organization.stripe_customer_id,
                name=customer_name,
                email=billing_email,
                metadata=customer_metadata,
                idempotency_key=(
                    f"scanx-customer-update-"
                    f"{organization.id}-"
                    f"{context.referral.id}"
                ),
            )

            return str(customer["id"])

        customer = stripe.Customer.create(
            name=customer_name,
            email=billing_email,
            metadata=customer_metadata,
            idempotency_key=(
                f"scanx-customer-{organization.id}"
            ),
        )

        return str(customer["id"])

    @staticmethod
    def _invoice_line_count(
        invoice: Any,
    ) -> int:
        lines = invoice.get("lines") or {}

        total_count = lines.get("total_count")

        if total_count is not None:
            return int(total_count)

        line_data = lines.get("data") or []

        return len(line_data)

    def create_and_send_invoice(
        self,
        *,
        context: BillingContext,
        amount_cents: int,
        description: str,
        idempotency_key: str,
    ) -> StripeInvoiceResult:
        if amount_cents <= 0:
            raise ValueError(
                "Organization invoice amount must "
                "be greater than zero."
            )

        if not description.strip():
            raise ValueError(
                "Organization invoice description "
                "must not be empty."
            )

        if not context.billing_email:
            raise ValueError(
                "Organization billing email is missing."
            )

        customer_id = self._get_or_create_customer(
            context
        )

        payment_terms_days = max(
            context.organization.payment_terms_days,
            0,
        )

        metadata = self._metadata(context)

        invoice_params: dict[str, Any] = {
            "customer": customer_id,
            "collection_method": (
                settings
                .stripe_invoice_collection_method
            ),
            "auto_advance": False,
            "metadata": metadata,
        }

        if (
            settings.stripe_invoice_collection_method
            == "send_invoice"
        ):
            invoice_params["days_until_due"] = (
                payment_terms_days
            )

        # Step 1:
        # Create a specific draft invoice for this referral.
        invoice = stripe.Invoice.create(
            **invoice_params,
            idempotency_key=(
                f"{idempotency_key}-invoice"
            ),
        )

        invoice_id = str(invoice["id"])

        # Step 2:
        # Attach the full organization charge directly
        # to this exact invoice.
        #
        # This prevents the appointment charge from
        # remaining as an unattached pending invoice item.
        stripe.InvoiceItem.create(
            customer=customer_id,
            invoice=invoice_id,
            amount=amount_cents,
            currency=(
                settings.stripe_default_currency
            ),
            description=description,
            metadata=metadata,
            idempotency_key=(
                f"{idempotency_key}-item"
            ),
        )

        # Step 3:
        # Retrieve the draft invoice and verify that Stripe
        # included the expected invoice line and total.
        invoice_before_finalize = (
            stripe.Invoice.retrieve(
                invoice_id,
                expand=["lines"],
            )
        )

        line_count = self._invoice_line_count(
            invoice_before_finalize
        )

        if line_count <= 0:
            raise ValueError(
                "Stripe draft invoice contains no "
                "invoice line items."
            )

        subtotal = int(
            invoice_before_finalize.get(
                "subtotal",
                0,
            )
            or 0
        )

        total = int(
            invoice_before_finalize.get(
                "total",
                0,
            )
            or 0
        )

        if subtotal <= 0:
            raise ValueError(
                "Stripe draft invoice subtotal is zero "
                "after attaching the invoice item."
            )

        if total <= 0:
            raise ValueError(
                "Stripe draft invoice total is zero "
                "after attaching the invoice item."
            )

        if total != amount_cents:
            raise ValueError(
                "Stripe draft invoice total does not "
                "match the expected organization "
                f"billing amount. Expected "
                f"{amount_cents} cents, received "
                f"{total} cents."
            )

        # Step 4:
        # Finalize the invoice so it becomes payable.
        finalized = stripe.Invoice.finalize_invoice(
            invoice_id,
            idempotency_key=(
                f"{idempotency_key}-finalize"
            ),
        )

        finalized_amount_due = int(
            finalized.get("amount_due", 0)
            or 0
        )

        if finalized_amount_due <= 0:
            raise ValueError(
                "Stripe finalized invoice amount_due "
                "is zero."
            )

        if finalized_amount_due != amount_cents:
            raise ValueError(
                "Stripe finalized invoice amount_due "
                "does not match the expected "
                "organization billing amount. "
                f"Expected {amount_cents} cents, "
                f"received "
                f"{finalized_amount_due} cents."
            )

        # Step 5:
        # For send_invoice collection, tell Stripe to
        # email the finalized invoice to the customer.
        sent = finalized

        if (
            settings.stripe_invoice_collection_method
            == "send_invoice"
        ):
            sent = stripe.Invoice.send_invoice(
                invoice_id,
                idempotency_key=(
                    f"{idempotency_key}-send"
                ),
            )

        transitions = (
            sent.get("status_transitions")
            or {}
        )

        finalized_at = (
            self._timestamp_to_datetime(
                transitions.get("finalized_at")
            )
        )

        due_at = self._timestamp_to_datetime(
            sent.get("due_date")
        )

        return StripeInvoiceResult(
            customer_id=customer_id,
            invoice_id=str(sent["id"]),
            invoice_number=sent.get("number"),
            finalized_at=finalized_at,
            sent_at=datetime.now(timezone.utc),
            due_at=due_at,
        )