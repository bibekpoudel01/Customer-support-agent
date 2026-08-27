from sqlalchemy import select

from src.sql.database import SessionLocal
from src.sql.orm import Product, Ticket, Order, Customer
from src.sql.schemas import (
    ProductOut,
    ProductLookupResult,
    ProductSearchResult,
    TicketOut,
    TicketCreateResult,
    CustomerOut,
    OrderOut,
    OrderLookupResult,
)


def get_product_by_id(product_id: int) -> ProductLookupResult:
    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if not product or not product.active:
            return ProductLookupResult(found=False, reason="not_in_catalog")
        return ProductLookupResult(found=True, product=ProductOut.model_validate(product))


def get_product_by_name(product_name: str) -> ProductLookupResult:
    with SessionLocal() as session:
        stmt = (
            select(Product)
            .where(
                Product.product_name.ilike(f"%{product_name}%"),
                Product.active.is_(True),
            )
            .limit(1)
        )
        product = session.execute(stmt).scalar_one_or_none()
        if not product:
            return ProductLookupResult(found=False, reason="not_in_catalog")
        return ProductLookupResult(found=True, product=ProductOut.model_validate(product))


def check_stock(product_id: int) -> ProductLookupResult:
    """Always reflects the live stock_qty column, so this is correct
    right after place_order/cancel_order commit — no caching involved."""
    return get_product_by_id(product_id)


def search_products(
    category: str | None = None,
    max_price: float | None = None,
    keyword: str | None = None,
) -> ProductSearchResult:
    with SessionLocal() as session:
        stmt = select(Product).where(Product.active.is_(True))

        if category:
            stmt = stmt.where(Product.category.ilike(f"%{category}%"))
        if max_price is not None:
            stmt = stmt.where(Product.price.is_not(None), Product.price <= max_price)
        if keyword:
            stmt = stmt.where(
                Product.product_name.ilike(f"%{keyword}%")
                | Product.tags.ilike(f"%{keyword}%")
            )

        products = session.execute(stmt).scalars().all()
        if not products:
            return ProductSearchResult(found=False, products=[])
        return ProductSearchResult(found=True, products=[ProductOut.model_validate(p) for p in products])


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


def get_customer_by_session(session_id: str) -> CustomerOut | None:
    """Look up the customer tied to the authenticated session behind
    this chat — pass a stable auth/user id, not the LangGraph thread_id."""
    with SessionLocal() as session:
        stmt = select(Customer).where(Customer.session_id == session_id).limit(1)
        customer = session.execute(stmt).scalar_one_or_none()
        return CustomerOut.model_validate(customer) if customer else None


def create_ticket(session_id: str, reason: str, transcript: str | None = None) -> TicketCreateResult:
    with SessionLocal() as session:
        ticket = Ticket(session_id=session_id, reason=reason, transcript=transcript)
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return TicketCreateResult(created=True, ticket=TicketOut.model_validate(ticket))


def get_customer_summary(customer_id: int) -> str:
    """One tool for 'show me my details' — profile + order history in one call."""
    profile = get_customer_profile(customer_id)
    if not profile:
        return "I couldn't find a customer profile for this account."

    orders = get_orders_by_customer(customer_id)
    if not orders:
        return f"{profile.full_name or 'You'} have no orders yet."

    lines = [f"Orders for {profile.full_name or 'you'}:"]
    for o in orders:
        lines.append(
            f"- Order #{o.order_id}: {o.quantity} unit(s), status: {o.status}, total: Rs. {o.total_price:.2f}"
        )
    return "\n".join(lines)