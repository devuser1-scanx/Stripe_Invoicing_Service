from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Appointment(Base):
    __tablename__ = "appointment"
    __table_args__ = {"extend_existing": True}

    appointment_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    appointment_type: Mapped[str | None] = mapped_column(String(150))
    category: Mapped[str | None] = mapped_column(String(50))
    date: Mapped[date | None] = mapped_column(Date)
    time: Mapped[str | None] = mapped_column(String(20))
    duration: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    amount_paid: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    paid: Mapped[bool | None] = mapped_column(Boolean)
    calendar: Mapped[str | None] = mapped_column(String(100))
    status_label: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
