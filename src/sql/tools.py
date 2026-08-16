from sqlalchemy import select

from src.sql.database import SessionLocal
from src.sql.orm import Product, Ticket
from src.sql.api import (
    ProductOut,
    ProductLookupResult,
    ProductSearchResult,
    TicketOut,
    TicketCreateResult,
)


def get_product_by_id(product_id: int) -> ProductLookupResult:
    with SessionLocal() as session:
        product = session.get(Product, product_id)

        if not product or not product.active:
            return ProductLookupResult(
                found=False,
                reason="not_in_catalog"
            )

        return ProductLookupResult(
            found=True,
            product=ProductOut.model_validate(product)
        )


def get_product_by_name(product_name: str) -> ProductLookupResult:
    with SessionLocal() as session:
        stmt = (
            select(Product)
            .where(
                Product.product_name.ilike(f"%{product_name}%"),
                Product.active.is_(True)
            )
            .limit(1)
        )

        product = session.execute(stmt).scalar_one_or_none()

        if not product:
            return ProductLookupResult(
                found=False,
                reason="not_in_catalog"
            )

        return ProductLookupResult(
            found=True,
            product=ProductOut.model_validate(product)
        )


def check_stock(product_id: int) -> ProductLookupResult:
    result = get_product_by_id(product_id)

    if result.found and result.product.stock_qty is None:
        return ProductLookupResult(
            found=False,
            reason="stock_data_unavailable"
        )

    return result


def search_products(
    category: str | None = None,
    max_price: float | None = None,
    keyword: str | None = None,
) -> ProductSearchResult:

    with SessionLocal() as session:

        stmt = select(Product).where(
            Product.active.is_(True)
        )

        if category:
            stmt = stmt.where(
                Product.category.ilike(f"%{category}%")
            )

        if max_price is not None:
            stmt = stmt.where(
                Product.price.is_not(None),
                Product.price <= max_price
            )

        if keyword:
            stmt = stmt.where(
                Product.product_name.ilike(f"%{keyword}%")
                | Product.tags.ilike(f"%{keyword}%")
            )

        products = session.execute(stmt).scalars().all()

        if not products:
            return ProductSearchResult(
                found=False,
                products=[]
            )

        return ProductSearchResult(
            found=True,
            products=[
                ProductOut.model_validate(p)
                for p in products
            ]
        )


# ============================================================
# TICKET TOOLS
# The agent calls this itself when it can't answer something
# (from RAG or from the Product table) and needs to hand off
# to a human. This is the only thing the agent WRITES.
# ============================================================

def create_ticket(
    session_id: str,
    reason: str,
    transcript: str | None = None,
) -> TicketCreateResult:

    with SessionLocal() as session:
        ticket = Ticket(
            session_id=session_id,
            reason=reason,
            transcript=transcript,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)

        return TicketCreateResult(
            created=True,
            ticket=TicketOut.model_validate(ticket)
        )