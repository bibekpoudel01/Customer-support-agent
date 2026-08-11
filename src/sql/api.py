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
    reserved_qty: int = 0
    lead_time_days: Optional[int] = None


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

    customer_id: str
    session_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    verified: bool = False


class CustomerLookupResult(BaseModel):
    found: bool
    customer: Optional[CustomerOut] = None




class OrderItemOut(BaseModel):
    product_id: int
    qty: int
    unit_price: float


class PaymentOut(BaseModel):
    amount: float
    status: str
    transaction_ref: Optional[str] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    status: str
    order_date: str
    eta_date: Optional[str] = None
    tracking_number: Optional[str] = None
    total_amount: Optional[float] = None

    items: list[OrderItemOut] = Field(default_factory=list)
    payments: list[PaymentOut] = Field(default_factory=list)


class OrderLookupResult(BaseModel):
    found: bool
    order: Optional[OrderOut] = None
    reason: Optional[str] = None