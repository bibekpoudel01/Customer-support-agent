import json
from datetime import datetime
from pathlib import Path

from src.sql.database import SessionLocal, init_db
from src.sql.orm import (
    Product, Customer, Address, PaymentMethod, Order, OrderItem, Payment,
    OrderStatus, PaymentStatus, PaymentType,
)

HERE = Path(__file__).parent
PRODUCT_SOURCE = HERE.parent.parent / "DATA" / "true_data" / "product.json"


def load_products(json_path: str) -> None:
    with open(json_path) as f:
        products = json.load(f)

    with SessionLocal() as session:
        for p in products:
            session.merge(Product(
                product_id=p["product_id"],
                product_name=p["product_name"],
                category=p["category"],
                brand=p.get("brand"),
                price=p.get("price"),      # backfill required
                stock_qty=p.get("stock_qty"),  # backfill required
                reserved_qty=0,
                lead_time_days=None,
                short_description=p.get("short_description"),
                tags=p.get("tags"),
                key_features_json=json.dumps(p.get("key_features", [])),
                specs_json=json.dumps(p.get("specifications", {})),
            ))
        session.commit()
        print(f"Loaded {len(products)} products.")


