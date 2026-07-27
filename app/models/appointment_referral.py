import uuid
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppointmentReferral(Base):
    __tablename__ = "appointment_referrals"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    appointment_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    referral_code_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    referral_status: Mapped[str] = mapped_column(String(40), nullable=False)
    billing_responsibility: Mapped[str] = mapped_column(String(30), nullable=False)
    purchase_order_number: Mapped[str | None] = mapped_column(String(150))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column()
