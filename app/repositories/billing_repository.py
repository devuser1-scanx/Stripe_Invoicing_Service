import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    AppointmentReferral,
    OrganizationInvoice,
    ReferralOrganization,
    ReferralOrganizationContact,
)


@dataclass(frozen=True)
class BillingContext:
    referral: AppointmentReferral
    appointment: Appointment
    organization: ReferralOrganization
    billing_email: str | None
    existing_invoice: OrganizationInvoice | None


class BillingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_context(self, appointment_referral_id: uuid.UUID) -> BillingContext | None:
        referral = self.db.get(AppointmentReferral, appointment_referral_id)
        if referral is None:
            return None

        appointment = self.db.get(Appointment, referral.appointment_id)
        organization = self.db.get(ReferralOrganization, referral.organization_id)
        if appointment is None or organization is None:
            return None

        contact_stmt: Select[tuple[ReferralOrganizationContact]] = (
            select(ReferralOrganizationContact)
            .where(
                ReferralOrganizationContact.organization_id == organization.id,
                ReferralOrganizationContact.is_active.is_(True),
                ReferralOrganizationContact.can_receive_invoices.is_(True),
                ReferralOrganizationContact.email.is_not(None),
            )
            .order_by(
                ReferralOrganizationContact.is_primary.desc(),
                ReferralOrganizationContact.contact_type.asc(),
            )
            .limit(1)
        )
        contact = self.db.scalar(contact_stmt)

        invoice_stmt = select(OrganizationInvoice).where(
            OrganizationInvoice.appointment_referral_id == appointment_referral_id
        )
        existing_invoice = self.db.scalar(invoice_stmt)

        billing_email = (
            contact.email
            if contact is not None
            else organization.billing_email or organization.primary_email
        )

        return BillingContext(
            referral=referral,
            appointment=appointment,
            organization=organization,
            billing_email=billing_email,
            existing_invoice=existing_invoice,
        )

    def reserve_invoice(
        self,
        *,
        appointment_referral_id: uuid.UUID,
        appointment_id: str,
        organization_id: uuid.UUID,
        amount: Decimal,
        service_description: str,
        service_date,
    ) -> uuid.UUID | None:
        invoice_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        stmt = (
            insert(OrganizationInvoice)
            .values(
                id=invoice_id,
                organization_id=organization_id,
                appointment_id=appointment_id,
                appointment_referral_id=appointment_referral_id,
                service_description=service_description,
                subtotal_amount=amount,
                discount_amount=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                total_amount=amount,
                currency="USD",
                billing_status="draft",
                payment_status="processing",
                service_date=service_date,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["appointment_referral_id"])
            .returning(OrganizationInvoice.id)
        )

        reserved_id = self.db.scalar(stmt)
        if reserved_id is not None:
            self.db.commit()
        else:
            self.db.rollback()

        return reserved_id

    def mark_invoice_sent(
        self,
        *,
        organization_invoice_id: uuid.UUID,
        stripe_customer_id: str,
        stripe_invoice_id: str,
        stripe_invoice_number: str | None,
        finalized_at: datetime | None,
        sent_at: datetime,
        due_at: datetime | None,
    ) -> None:
        invoice = self.db.get(OrganizationInvoice, organization_invoice_id)
        if invoice is None:
            raise RuntimeError("Reserved invoice disappeared")

        invoice.stripe_customer_id = stripe_customer_id
        invoice.stripe_invoice_id = stripe_invoice_id
        invoice.internal_invoice_number = stripe_invoice_number
        invoice.billing_status = "sent"
        invoice.payment_status = "unpaid"
        invoice.invoice_finalized_at = finalized_at
        invoice.invoice_sent_at = sent_at
        invoice.due_at = due_at
        invoice.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def mark_invoice_failed(self, organization_invoice_id: uuid.UUID) -> None:
        invoice = self.db.get(OrganizationInvoice, organization_invoice_id)
        if invoice is None:
            return

        # Existing schema has no failed billing_status. Keep draft and mark payment failed.
        invoice.billing_status = "draft"
        invoice.payment_status = "failed"
        invoice.updated_at = datetime.now(timezone.utc)
        self.db.commit()
