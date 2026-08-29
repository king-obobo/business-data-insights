-- ============================================================
-- Apple Retail Sales Database Schema
-- ============================================================

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS warranty;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS category;


-- ============================================================
-- CATEGORY
-- ============================================================

CREATE TABLE category (
    category_id   INTEGER PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);


-- ============================================================
-- STORES
-- ============================================================

CREATE TABLE stores (
    store_id   INTEGER PRIMARY KEY,
    store_name VARCHAR(150) NOT NULL,
    city       VARCHAR(100) NOT NULL,
    country    VARCHAR(100) NOT NULL
);


-- ============================================================
-- PRODUCTS
-- ============================================================

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category_id  INTEGER NOT NULL,
    launch_date  DATE,
    price        NUMERIC(10, 2) NOT NULL,

    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id)
        REFERENCES category(category_id),

    CONSTRAINT chk_products_price
        CHECK (price >= 0)
);


-- ============================================================
-- SALES
-- ============================================================

CREATE TABLE sales (
    sale_id    BIGINT PRIMARY KEY,
    sale_date  DATE NOT NULL,
    store_id   INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL,

    CONSTRAINT fk_sales_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id),

    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    CONSTRAINT chk_sales_quantity
        CHECK (quantity > 0)
);


-- ============================================================
-- WARRANTY
-- ============================================================

CREATE TABLE warranty (
    claim_id      INTEGER PRIMARY KEY,
    claim_date    DATE NOT NULL,
    sale_id       BIGINT NOT NULL,
    repair_status VARCHAR(50) NOT NULL,

    CONSTRAINT fk_warranty_sale
        FOREIGN KEY (sale_id)
        REFERENCES sales(sale_id)
);


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_products_category_id
    ON products(category_id);

CREATE INDEX idx_sales_store_id
    ON sales(store_id);

CREATE INDEX idx_sales_product_id
    ON sales(product_id);

CREATE INDEX idx_warranty_sale_id
    ON warranty(sale_id);