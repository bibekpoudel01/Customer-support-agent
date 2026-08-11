import enum
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.sql.database import Base



class OrderStatus(str, enum.Enum):
    placed = "placed"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


# ============================================================
# PRODUCT
# ============================================================

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

    # Dynamic/current information → SQL
    price: Mapped[float | None] = mapped_column(Float)

    stock_qty: Mapped[int | None] = mapped_column(Integer)

    reserved_qty: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    lead_time_days: Mapped[int | None] = mapped_column(
        Integer
    )

    # Basic product information
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

    # Track dynamic data changes
    stock_updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    price_updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="product"
    )


# ============================================================
# CUSTOMER
# ============================================================

class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(
        String,
        primary_key=True
    )

    session_id: Mapped[str | None] = mapped_column(
        String,
        index=True
    )

    name: Mapped[str | None] = mapped_column(
        String
    )

    email: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        index=True
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer"
    )

    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="customer"
    )


# ============================================================
# ORDER
# ============================================================

class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(
        String,
        primary_key=True
    )

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.customer_id"),
        index=True
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus),
        nullable=False,
        index=True
    )

    order_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    eta_date: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    tracking_number: Mapped[str | None] = mapped_column(
        String
    )

    total_amount: Mapped[float | None] = mapped_column(
        Float
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="orders"
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order"
    )


# ============================================================
# ORDER ITEM
# ============================================================

class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"),
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"),
        index=True
    )

    qty: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )

    # Price at the time of purchase
    unit_price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    order: Mapped["Order"] = relationship(
        back_populates="items"
    )

    product: Mapped["Product"] = relationship(
        back_populates="order_items"
    )


# ============================================================
# PAYMENT
# ============================================================

class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"),
        index=True
    )

    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus),
        nullable=False,
        index=True
    )

    transaction_ref: Mapped[str | None] = mapped_column(
        String
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime
    )

    order: Mapped["Order"] = relationship(
        back_populates="payments"
    )


# ============================================================
# SUPPORT TICKET
# ============================================================

class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    customer_id: Mapped[str | None] = mapped_column(
        ForeignKey("customers.customer_id")
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

    customer: Mapped["Customer | None"] = relationship(
        back_populates="tickets"
    )