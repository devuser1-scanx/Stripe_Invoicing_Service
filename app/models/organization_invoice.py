import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganizationInvoice(Base):
    """
    Maps the existing organization_invoices table.

    This model intentionally matches the current ScanX schema rather than
    creating a second invoice table.
    """

    __tablename__ = "organization_invoices"
    __table_args__ = (
        UniqueConstraint(
            "appointment_referral_id",
            name="uq_org_invoice_appointment_referral",
        ),
        CheckConstraint(
            "subtotal_amount >= 0 AND discount_amount >= 0 "
            "AND tax_amount >= 0 AND total_amount >= 0",
            name="organization_invoice_amounts_check",
        ),
        CheckConstraint(
            "total_amount = subtotal_amount - discount_amount + tax_amount",
            name="organization_invoice_total_check",
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("referral_organizations.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    appointment_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("appointment.appointment_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    appointment_referral_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointment_referrals.id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )

    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    internal_invoice_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    service_description: Mapped[str | None] = mapped_column(String(255))

    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    billing_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="draft"
    )
    payment_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="unpaid"
    )

    service_date: Mapped[date | None] = mapped_column(Date)
    invoice_finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invoice_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    report_delivery_status: Mapped[str | None] = mapped_column(String(30))
    report_delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_stripe_event_id: Mapped[str | None] = mapped_column(String(150))

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
