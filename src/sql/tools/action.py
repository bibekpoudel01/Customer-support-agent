from langchain_core.tools import tool
from src.sql.database import SessionLocal
from src.sql.orm import Order, OrderStatus, Product

HIGH_VALUE_THRESHOLD = 500.0


def _get_order(session, order_id: int) -> Order | None:
    return session.get(Order, order_id)


def is_high_risk(order_id: int) -> bool:
    with SessionLocal() as session:
        order = _get_order(session, order_id)
        if not order:
            return True
        return (order.total_price or 0) >= HIGH_VALUE_THRESHOLD


@tool
def place_order(customer_id: int, product_id: int, quantity: int) -> str:
    """Place a new order after the user has explicitly confirmed the quantity
    and product. Deducts stock and creates the order in one transaction.
    The agent must ask the user 'X units of Y, confirm?' and get a yes
    BEFORE calling this tool — do not call it on the first mention of a product."""
    with SessionLocal() as session:
        product = session.get(Product, product_id)

        if not product or not product.active:
            return f"Product ID {product_id} is unavailable or does not exist."

        if product.stock_qty is None or product.stock_qty < quantity:
            return f"Insufficient stock for {product.product_name}. Available: {product.stock_qty or 0}."

        total_price = (product.price or 0.0) * quantity
        product.stock_qty -= quantity  # fixed: was referencing an undefined `quantitys`

        new_order = Order(
            customer_id=customer_id,
            product_id=product_id,
            quantity=quantity,
            status=OrderStatus.confirmed,
            total_price=total_price,
        )
        session.add(new_order)
        session.commit()
        session.refresh(new_order)

        return (
            f"{quantity} unit(s) of {product.product_name} added to your order "
            f"(Order #{new_order.order_id}). Total: Rs. {total_price:.2f}. "
            f"Please proceed with payment to ship it."
        )


@tool
def cancel_order(order_id: int) -> str:
    """Cancel an order and restore its stock to the catalog.
    HIGH RISK if order total >= Rs. 500 — must go through human approval
    before this tool is invoked for such orders."""
    with SessionLocal() as session:
        order = _get_order(session, order_id)
        if not order:
            return f"No order found with ID {order_id}."
        if order.status in (OrderStatus.cancelled, OrderStatus.refunded):
            return f"Order {order_id} is already {order.status.value}."
        if order.status in (OrderStatus.shipped, OrderStatus.delivered):
            return f"Order {order_id} cannot be cancelled — it is already {order.status.value}."

        order.status = OrderStatus.cancelled

        product = session.get(Product, order.product_id)
        if product:
            product.stock_qty = (product.stock_qty or 0) + order.quantity

        session.commit()
        return f"Order {order_id} cancelled and {order.quantity} unit(s) returned to stock."


@tool
def request_refund(order_id: int, reason: str) -> str:
    """File a refund request for a delivered or shipped order."""
    with SessionLocal() as session:
        order = _get_order(session, order_id)
        if not order:
            return f"No order found with ID {order_id}."
        if order.status not in (OrderStatus.delivered, OrderStatus.shipped):
            return f"Order {order_id} is not eligible for refund (status: {order.status.value})."

        order.status = OrderStatus.refund_requested
        session.commit()
        return f"Refund requested for order {order_id}. Reason logged: {reason}"