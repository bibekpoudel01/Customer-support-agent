import json
from pathlib import Path

from src.sql.database import SessionLocal, init_db
from src.sql.orm import Product

HERE = Path(__file__).parent
PRODUCT_SOURCE = HERE / "product.json"


def load_products(json_path: str) -> None:
    """
    Load product data into the SQL database..
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
                    price=p.get("price"),
                    stock_qty=p.get("stock_qty"),
                    short_description=p.get("short_description"),
                    tags=p.get("tags"),
                )
            )
        session.commit()

    print(f"Loaded {len(products)} products.")


if __name__ == "__main__":
    init_db()
    load_products(str(PRODUCT_SOURCE))