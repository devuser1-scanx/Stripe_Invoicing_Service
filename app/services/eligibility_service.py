from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.repositories.billing_repository import BillingContext


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    amount: Decimal | None = None


class EligibilityService:
    BLOCKED_REFERRAL_STATUSES = {
        "rejected",
        "expired",
        "needs_review",
        "cancelled",
    }

    SUPPORTED_BILLING_RESPONSIBILITIES = {"organization"}

    def evaluate(self, context: BillingContext) -> EligibilityResult:
        appointment = context.appointment
        referral = context.referral
        organization = context.organization
        now = datetime.now(timezone.utc)

        if appointment.status_label != "Complete":
            return EligibilityResult(False, "appointment_not_complete")

        if referral.referral_status in self.BLOCKED_REFERRAL_STATUSES:
            return EligibilityResult(False, "referral_not_billable")

        if referral.billing_responsibility not in self.SUPPORTED_BILLING_RESPONSIBILITIES:
            return EligibilityResult(False, "billing_responsibility_not_supported")

        if organization.status != "active":
            return EligibilityResult(False, "organization_inactive")

        if organization.agreement_status != "active":
            return EligibilityResult(False, "agreement_inactive")

        if (
            organization.agreement_effective_at is not None
            and organization.agreement_effective_at > now
        ):
            return EligibilityResult(False, "agreement_not_effective")

        if (
            organization.agreement_expires_at is not None
            and organization.agreement_expires_at <= now
        ):
            return EligibilityResult(False, "agreement_expired")

        if context.existing_invoice is not None:
            return EligibilityResult(False, "invoice_already_exists")

        if context.billing_email is None:
            return EligibilityResult(False, "billing_email_missing")

        amount = appointment.price
        if amount is None:
            return EligibilityResult(False, "billing_amount_missing")

        if amount <= Decimal("0.00"):
            return EligibilityResult(False, "billing_amount_zero")

        return EligibilityResult(True, "eligible", amount=amount)
