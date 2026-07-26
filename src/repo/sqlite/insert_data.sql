
CREATE TABLE brands (
    brand_id     SERIAL PRIMARY KEY,
    brand_name   VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE categories (
    category_id         SERIAL PRIMARY KEY,
    category_name       VARCHAR(100) NOT NULL,
    parent_category_id  INTEGER REFERENCES categories(category_id)
);

CREATE TABLE products (
    product_id      SERIAL PRIMARY KEY,
    sku             VARCHAR(50) NOT NULL UNIQUE,
    product_name    VARCHAR(200) NOT NULL,
    category_id     INTEGER NOT NULL REFERENCES categories(category_id),
    brand_id        INTEGER REFERENCES brands(brand_id),
    description     TEXT,
    product_url     VARCHAR(500),
    current_price   NUMERIC(10,2) NOT NULL,
    discount_pct    NUMERIC(5,2)  DEFAULT 0 CHECK (discount_pct >= 0 AND discount_pct <= 100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE product_images (
    image_id     SERIAL PRIMARY KEY,
    product_id   INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    image_url    VARCHAR(500) NOT NULL,
    sort_order   INTEGER DEFAULT 0
);

CREATE TABLE inventory (
    product_id          INTEGER PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
    stock_quantity      INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    stock_availability  VARCHAR(20) NOT NULL DEFAULT 'in_stock', 
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE product_ratings (
    product_id    INTEGER PRIMARY KEY REFERENCES products(product_id) ON DELETE CASCADE,
    avg_rating    NUMERIC(3,2) DEFAULT 0,
    review_count  INTEGER DEFAULT 0
);

CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(150),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_preferences (
    user_id       INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    preferences   JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
    review_id     SERIAL PRIMARY KEY,
    product_id    INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    user_id       INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE TABLE orders (
    order_id       SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(user_id),
    order_status   VARCHAR(30) NOT NULL DEFAULT 'pending', -- pending/confirmed/cancelled/completed
    total_amount   NUMERIC(10,2) NOT NULL,
    coupon_id      INTEGER, -- FK added after coupons table is created
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    order_item_id  SERIAL PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id     INTEGER NOT NULL REFERENCES products(product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     NUMERIC(10,2) NOT NULL
);

CREATE TABLE payments (
    payment_id       SERIAL PRIMARY KEY,
    order_id         INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    payment_method   VARCHAR(30) NOT NULL, -- card/paypal/cod/etc
    payment_status   VARCHAR(30) NOT NULL DEFAULT 'pending', -- pending/paid/failed/refunded
    amount           NUMERIC(10,2) NOT NULL,
    transaction_ref  VARCHAR(100),
    paid_at          TIMESTAMPTZ
);

CREATE TABLE shipments (
    shipment_id      SERIAL PRIMARY KEY,
    order_id         INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    carrier          VARCHAR(50),
    tracking_number  VARCHAR(100),
    shipping_status  VARCHAR(30) NOT NULL DEFAULT 'processing', -- processing/shipped/in_transit/delivered/returned
    shipped_at       TIMESTAMPTZ,
    delivered_at     TIMESTAMPTZ
);

-- ---------- Coupons ----------

CREATE TABLE coupons (
    coupon_id       SERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    discount_type   VARCHAR(20) NOT NULL, -- percent / fixed
    discount_value  NUMERIC(10,2) NOT NULL,
    valid_from      TIMESTAMPTZ,
    valid_to        TIMESTAMPTZ,
    usage_limit     INTEGER,
    times_used      INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE orders
    ADD CONSTRAINT fk_orders_coupon FOREIGN KEY (coupon_id) REFERENCES coupons(coupon_id);



CREATE TABLE conversation_history (
    conversation_id  SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    message_role     VARCHAR(20) NOT NULL, -- user / assistant / system
    message_text     TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE search_history (
    search_id    SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    query_text   VARCHAR(500) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE product_views (
    view_id      SERIAL PRIMARY KEY,
    product_id   INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    user_id      INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    viewed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Audit logs (generic, for any frequently-changing table) ----------

CREATE TABLE audit_logs (
    log_id       BIGSERIAL PRIMARY KEY,
    table_name   VARCHAR(100) NOT NULL,
    record_id    VARCHAR(100) NOT NULL,
    action       VARCHAR(20) NOT NULL, -- insert/update/delete
    changed_by   INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    old_data     JSONB,
    new_data     JSONB,
    changed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- Helpful indexes ----------

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_product_views_product ON product_views(product_id);
CREATE INDEX idx_audit_logs_table_record ON audit_logs(table_name, record_id);





