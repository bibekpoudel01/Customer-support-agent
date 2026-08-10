
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.sql.database import SessionLocal
from src.sql.orm import Product, Customer, Order, PaymentMethod
from src.sql.api import (
    ProductOut, ProductLookupResult, ProductSearchResult,
    CustomerOut, CustomerLookupResult,
    OrderOut, OrderLookupResult,
    PaymentMethodOut, PaymentMethodsResult,
)


def get_product_by_id(product_id: int) -> ProductLookupResult:
    with SessionLocal() as session:
        product = session.get(Product, product_id)
        if not product or not product.active:
            return ProductLookupResult(found=False, reason="not_in_catalog")
        return ProductLookupResult(found=True, product=ProductOut.model_validate(product))


def get_product_by_name(product_name: str) -> ProductLookupResult:
    with SessionLocal() as session:
        stmt = select(Product).where(
            Product.product_name.ilike(f"%{product_name}%"), Product.active.is_(True)
        ).limit(1)
        product = session.execute(stmt).scalar_one_or_none()
        if not product:
            return ProductLookupResult(found=False, reason="not_in_catalog")
        return ProductLookupResult(found=True, product=ProductOut.model_validate(product))


def check_stock(product_id: int) -> ProductLookupResult:
    result = get_product_by_id(product_id)
    if result.found and result.product.stock_qty is None:
        # price/stock not backfilled — "unknown" is not the same as "in stock"
        return ProductLookupResult(found=False, reason="stock_data_unavailable")
    return result


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
                Product.product_name.ilike(f"%{keyword}%") | Product.tags.ilike(f"%{keyword}%")
            )
        products = session.execute(stmt).scalars().all()
        if not products:
            return ProductSearchResult(found=False, products=[])
        return ProductSearchResult(
            found=True, products=[ProductOut.model_validate(p) for p in products]
        )


def get_customer_by_session(session_id: str) -> CustomerLookupResult:
    with SessionLocal() as session:
        stmt = select(Customer).where(Customer.session_id == session_id)
        customer = session.execute(stmt).scalar_one_or_none()
        if not customer:
            return CustomerLookupResult(found=False)
        return CustomerLookupResult(found=True, customer=CustomerOut.model_validate(customer))


def get_order_status(order_id: str, session_id: str) -> OrderLookupResult:
    """Requires the session's verified customer to own the order — never
    return order details without this check (cross-customer data leak)."""
    customer_result = get_customer_by_session(session_id)
    if not customer_result.found or not customer_result.customer.verified:
        return OrderLookupResult(found=False, reason="not_verified")

    with SessionLocal() as session:
        stmt = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.payments))
            .where(Order.order_id == order_id, Order.customer_id == customer_result.customer.customer_id)
        )
        order = session.execute(stmt).scalar_one_or_none()
        if not order:
            return OrderLookupResult(found=False, reason="not_found")

        return OrderLookupResult(
            found=True,
            order=OrderOut(
                order_id=order.order_id,
                status=order.status.value,
                order_date=order.order_date.isoformat(),
                eta_date=order.eta_date.isoformat() if order.eta_date else None,
                tracking_number=order.tracking_number,
                total_amount=order.total_amount,
                items=[
                    {"product_id": i.product_id, "qty": i.qty, "unit_price": i.unit_price}
                    for i in order.items
                ],
                payments=[
                    {"amount": p.amount, "status": p.status.value, "transaction_ref": p.transaction_ref}
                    for p in order.payments
                ],
            ),
        )


def get_payment_methods(session_id: str) -> PaymentMethodsResult:
    """Returns masked payment methods (type/provider/last4 only) —
    never expose full card numbers, this table doesn't store them."""
    customer_result = get_customer_by_session(session_id)
    if not customer_result.found or not customer_result.customer.verified:
        return PaymentMethodsResult(found=False)

    with SessionLocal() as session:
        stmt = select(PaymentMethod).where(
            PaymentMethod.customer_id == customer_result.customer.customer_id
        )
        methods = session.execute(stmt).scalars().all()
        if not methods:
            return PaymentMethodsResult(found=False)
        return PaymentMethodsResult(
            found=True,
            payment_methods=[
                PaymentMethodOut(
                    payment_method_id=m.payment_method_id,
                    type=m.type.value,
                    provider=m.provider,
                    last4=m.last4,
                    is_default=m.is_default,
                )
                for m in methods
            ],
        )