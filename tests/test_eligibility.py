from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.services.eligibility_service import EligibilityService


def context(**overrides):
    base = {
        "appointment": SimpleNamespace(status_label="Complete", price=Decimal("124.00")),
        "referral": SimpleNamespace(
            referral_status="pending_verification",
            billing_responsibility="organization",
        ),
        "organization": SimpleNamespace(
            status="active",
            agreement_status="active",
            agreement_effective_at=None,
            agreement_expires_at=None,
        ),
        "existing_invoice": None,
        "billing_email": "billing@example.com",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_pending_verification_is_billable() -> None:
    result = EligibilityService().evaluate(context())
    assert result.eligible is True
    assert result.reason == "eligible"


def test_verified_is_billable() -> None:
    c = context()
    c.referral.referral_status = "verified"
    result = EligibilityService().evaluate(c)
    assert result.eligible is True


def test_rejected_is_blocked() -> None:
    c = context()
    c.referral.referral_status = "rejected"
    result = EligibilityService().evaluate(c)
    assert result.eligible is False
    assert result.reason == "referral_not_billable"


def test_incomplete_appointment_is_blocked() -> None:
    c = context()
    c.appointment.status_label = "Checked-In"
    result = EligibilityService().evaluate(c)
    assert result.eligible is False
    assert result.reason == "appointment_not_complete"


def test_zero_amount_is_blocked() -> None:
    c = context()
    c.appointment.price = Decimal("0.00")
    result = EligibilityService().evaluate(c)
    assert result.eligible is False
    assert result.reason == "billing_amount_zero"


def test_expired_agreement_is_blocked() -> None:
    c = context()
    c.organization.agreement_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    result = EligibilityService().evaluate(c)
    assert result.eligible is False
    assert result.reason == "agreement_expired"
