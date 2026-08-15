import json
from pathlib import Path

from src.sql.database import SessionLocal, init_db
from src.sql.orm import Product


HERE = Path(__file__).parent

PRODUCT_SOURCE = (
    HERE / "product.json"
)


def load_products(json_path: str) -> None:
    """
    Load product data into the SQL database.

    SQL stores structured/dynamic product information such as:
    - price
    - stock
    - category
    - brand

    Static product knowledge such as detailed specifications,
    features, manuals, warranty, etc. should be handled by RAG.
    """

    with open(json_path, encoding="utf-8") as f:
        products = json.load(f)

    with SessionLocal() as session:

        for p in products:
            session.merge(
                Product(
                    product_id=p["product_id"],
                    product_name=p["product_name"],
                    category=p["category"],
                    brand=p.get("brand"),

                    # Dynamic product information
                    price=p.get("price"),
                    stock_qty=p.get("stock_qty"),
                    reserved_qty=0,
                    lead_time_days=None,

                    # Basic searchable information
                    short_description=p.get("short_description"),
                    tags=p.get("tags"),
                )
            )

        session.commit()

    print(f"Loaded {len(products)} products.")


