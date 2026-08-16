import enum
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.sql.database import Base


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"




class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    product_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )

    category: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )

    brand: Mapped[str | None] = mapped_column(String)

    price: Mapped[float | None] = mapped_column(Float)

    stock_qty: Mapped[int | None] = mapped_column(Integer)

    short_description: Mapped[str | None] = mapped_column(
        Text
    )

    tags: Mapped[str | None] = mapped_column(
        String
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )




class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    session_id: Mapped[str] = mapped_column(
        String,
        index=True
    )

    reason: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    transcript: Mapped[str | None] = mapped_column(
        Text
    )

    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus),
        default=TicketStatus.open,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )