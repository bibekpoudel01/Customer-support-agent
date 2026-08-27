from src.sql.orm import Order, Customer, OrderStatus
from src.sql.schemas import CustomerOut, OrderOut, OrderLookupResult
from sqlalchemy import select
from src.sql.database import SessionLocal
from src.sql.orm import Order, Customer
from src.sql.schemas import CustomerOut, OrderOut, OrderLookupResult
def get_order_by_id(order_id: int) -> OrderLookupResult:
    with SessionLocal() as session:
        order = session.get(Order, order_id)
        if not order:
            return OrderLookupResult(found=False, reason="order_not_found")
        return OrderLookupResult(found=True, order=OrderOut.model_validate(order))


def get_orders_by_customer(customer_id: int) -> list[OrderOut]:
    with SessionLocal() as session:
        stmt = select(Order).where(Order.customer_id == customer_id)
        orders = session.execute(stmt).scalars().all()
        return [OrderOut.model_validate(o) for o in orders]


def get_customer_profile(customer_id: int) -> CustomerOut | None:
    with SessionLocal() as session:
        customer = session.get(Customer, customer_id)
        return CustomerOut.model_validate(customer) if customer else None