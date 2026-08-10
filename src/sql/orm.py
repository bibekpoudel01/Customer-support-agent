
import enum
from datetime import datetime

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Enum as SAEnum
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


class PaymentType(str, enum.Enum):
    card = "card"
    paypal = "paypal"
    upi = "upi"
    wallet = "wallet"
    cod = "cod"  # cash on delivery


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String)
    price: Mapped[float | None] = mapped_column(Float)           # NULL until backfilled
    stock_qty: Mapped[int | None] = mapped_column(Integer)       # NULL until backfilled
    reserved_qty: Mapped[int] = mapped_column(Integer, default=0)  # reserved but not shipped
    lead_time_days: Mapped[int | None] = mapped_column(Integer)  # standard delivery estimate
    short_description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(String)
    key_features_json: Mapped[str | None] = mapped_column(Text)  # json.dumps(list[str])
    specs_json: Mapped[str | None] = mapped_column(Text)         # json.dumps(dict) — varies per category
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    stock_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    price_updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str | None] = mapped_column(String, index=True)
    name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    addresses: Mapped[list["Address"]] = relationship(back_populates="customer")
    payment_methods: Mapped[list["PaymentMethod"]] = relationship(back_populates="customer")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")


class Address(Base):
    __tablename__ = "addresses"

    address_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    label: Mapped[str | None] = mapped_column(String)  # "home", "work", etc.
    line1: Mapped[str] = mapped_column(String, nullable=False)
    line2: Mapped[str | None] = mapped_column(String)
    city: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str | None] = mapped_column(String)
    postal_code: Mapped[str | None] = mapped_column(String)
    country: Mapped[str] = mapped_column(String, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped["Customer"] = relationship(back_populates="addresses")
    orders: Mapped[list["Order"]] = relationship(back_populates="shipping_address")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    payment_method_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    type: Mapped[PaymentType] = mapped_column(SAEnum(PaymentType), nullable=False)
    provider: Mapped[str | None] = mapped_column(String)   # "Visa", "PayPal", "GPay" etc.
    last4: Mapped[str | None] = mapped_column(String)       # never store full card numbers
    expiry_month: Mapped[int | None] = mapped_column(Integer)
    expiry_year: Mapped[int | None] = mapped_column(Integer)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="payment_methods")
    payments: Mapped[list["Payment"]] = relationship(back_populates="payment_method")


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    shipping_address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.address_id"))
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), nullable=False, index=True)
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    eta_date: Mapped[datetime | None] = mapped_column(DateTime)
    tracking_number: Mapped[str | None] = mapped_column(String)
    total_amount: Mapped[float | None] = mapped_column(Float)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    shipping_address: Mapped["Address | None"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"), index=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)  # snapshot at order time

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    payment_method_id: Mapped[int | None] = mapped_column(ForeignKey("payment_methods.payment_method_id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), nullable=False, index=True)
    transaction_ref: Mapped[str | None] = mapped_column(String)  # external gateway reference
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)

    order: Mapped["Order"] = relationship(back_populates="payments")
    payment_method: Mapped["PaymentMethod | None"] = relationship(back_populates="payments")


class Ticket(Base):
    """Escalation record — written when the agent can't ground an answer
    or urgency is detected, per the escalation node in the agent graph."""
    __tablename__ = "tickets"

    ticket_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.customer_id"))
    session_id: Mapped[str] = mapped_column(String, index=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text)  # json.dumps(last N turns)
    status: Mapped[TicketStatus] = mapped_column(SAEnum(TicketStatus), default=TicketStatus.open, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    customer: Mapped["Customer | None"] = relationship(back_populates="tickets")