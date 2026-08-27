from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    category: str
    brand: Optional[str] = None
    price: Optional[float] = None
    stock_qty: Optional[int] = None
    short_description: Optional[str] = None
    tags: Optional[str] = None


class ProductLookupResult(BaseModel):
    found: bool
    product: Optional[ProductOut] = None
    reason: Optional[str] = None


class ProductSearchResult(BaseModel):
    found: bool
    products: list[ProductOut] = Field(default_factory=list)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int
    full_name: Optional[str] = None
    email: Optional[str] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    customer_id: int
    product_id: int
    quantity: int
    status: str
    total_price: Optional[float] = None


class OrderLookupResult(BaseModel):
    found: bool
    order: Optional[OrderOut] = None
    reason: Optional[str] = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: int
    status: str
    reason: str


class TicketCreateResult(BaseModel):
    created: bool
    ticket: Optional[TicketOut] = None