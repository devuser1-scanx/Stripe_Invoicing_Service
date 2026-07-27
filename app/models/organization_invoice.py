import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganizationInvoice(Base):
    __tablename__ = "organization_invoices"
    __table_args__ = (
        UniqueConstraint(
            "appointment_referral_id",
            name="uq_org_invoice_appointment_referral",
        ),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    appointment_id: Mapped[str] = mapped_column(String(50), nullable=False)
    appointment_referral_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    internal_invoice_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    service_description: Mapped[str | None] = mapped_column(String(255))

    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    billing_status: Mapped[str] = mapped_column(String(40), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False)
    service_date: Mapped[date | None] = mapped_column(Date)

    invoice_finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invoice_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_stripe_event_id: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
