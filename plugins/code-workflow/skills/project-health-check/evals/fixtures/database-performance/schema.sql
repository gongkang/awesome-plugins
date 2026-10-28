-- MySQL 8.4 合成验收数据的声明 schema，不代表任何线上部署状态。
CREATE TABLE customers (
    id BIGINT PRIMARY KEY,
    display_name VARCHAR(120) NOT NULL
);

CREATE TABLE orders (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL,
    KEY idx_orders_tenant_created (tenant_id, created_at, id),
    KEY idx_orders_customer (customer_id)
);

CREATE TABLE order_items (
    id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    KEY idx_items_order (order_id)
);

CREATE TABLE payments (
    id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    KEY idx_payments_order (order_id)
);

CREATE TABLE shipments (
    id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    KEY idx_shipments_order (order_id)
);
