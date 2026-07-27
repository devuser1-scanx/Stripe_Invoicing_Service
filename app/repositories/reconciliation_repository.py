from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.appointment_referral import AppointmentReferral
from app.models.organization_invoice import OrganizationInvoice
from app.schemas.reconciliation import ReconciliationCandidate


class ReconciliationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_missing_invoice_candidates(
        self,
        *,
        lookback_days: int,
        batch_size: int,
    ) -> list[ReconciliationCandidate]:
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(days=lookback_days)
        )

        statement = (
            select(
                AppointmentReferral.id.label(
                    "appointment_referral_id"
                ),
                AppointmentReferral.appointment_id,
                AppointmentReferral.organization_id,
            )
            .join(
                Appointment,
                Appointment.appointment_id
                == AppointmentReferral.appointment_id,
            )
            .outerjoin(
                OrganizationInvoice,
                OrganizationInvoice.appointment_referral_id
                == AppointmentReferral.id,
            )
            .where(
                Appointment.status_label == "Complete",
                Appointment.date >= cutoff.date(),
                OrganizationInvoice.id.is_(None),
            )
            .order_by(
                Appointment.date.asc(),
                AppointmentReferral.id.asc(),
            )
            .limit(batch_size)
        )

        rows = self.db.execute(statement).all()

        return [
            ReconciliationCandidate(
                appointment_referral_id=(
                    row.appointment_referral_id
                ),
                appointment_id=row.appointment_id,
                organization_id=row.organization_id,
            )
            for row in rows
        ]