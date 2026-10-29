-- STEP 1: Supabase SQL Editor에서 전체를 한 번에 실행합니다.
-- 신규 프로젝트용입니다. 같은 이름의 테이블이 있으면 덮어쓰지 않고 실패합니다.
BEGIN;

-- 스키마가 없으면 생성하고 서버 역할에 접근 권한을 부여합니다.
CREATE SCHEMA IF NOT EXISTS ch2;
GRANT USAGE ON SCHEMA ch2 TO service_role;

CREATE TABLE ch2.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL,
    password_hash text NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 100),
    phone text NOT NULL CHECK (length(btrim(phone)) BETWEEN 1 AND 30),
    address text NOT NULL CHECK (length(btrim(address)) BETWEEN 1 AND 500),
    auth_version integer NOT NULL DEFAULT 1 CHECK (auth_version > 0),
    deleted_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT users_email_format CHECK (
        email = lower(btrim(email)) AND email ~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'
        AND length(email) <= 254
    ),
    CONSTRAINT users_email_key UNIQUE (email)
);

CREATE TABLE ch2.products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sku text NOT NULL UNIQUE CHECK (length(btrim(sku)) BETWEEN 1 AND 50),
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 200),
    description text NOT NULL DEFAULT '',
    price bigint NOT NULL CHECK (price > 0),
    stock integer NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ch2.orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES ch2.users(id) ON DELETE RESTRICT,
    status text NOT NULL DEFAULT 'cart' CHECK (status IN ('cart', 'pending', 'paid')),
    total_amount bigint NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    recipient_name text,
    recipient_phone text,
    shipping_address text,
    ordered_at timestamptz,
    paid_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT orders_checkout_fields CHECK (
        (status = 'cart' AND ordered_at IS NULL AND total_amount = 0)
        OR
        (status IN ('pending', 'paid') AND ordered_at IS NOT NULL AND total_amount > 0
         AND recipient_name IS NOT NULL AND length(btrim(recipient_name)) BETWEEN 1 AND 100
         AND recipient_phone IS NOT NULL AND length(btrim(recipient_phone)) BETWEEN 1 AND 30
         AND shipping_address IS NOT NULL AND length(btrim(shipping_address)) BETWEEN 1 AND 500)
    ),
    CONSTRAINT orders_paid_at CHECK (
        (status = 'paid' AND paid_at IS NOT NULL)
        OR (status <> 'paid' AND paid_at IS NULL)
    )
);

-- 부분 UNIQUE 인덱스로 동시 요청에서도 회원당 장바구니를 하나로 제한합니다.
CREATE UNIQUE INDEX orders_one_cart_per_user ON ch2.orders (user_id) WHERE status = 'cart';
CREATE INDEX orders_user_history_idx ON ch2.orders (user_id, ordered_at DESC) WHERE status <> 'cart';

CREATE TABLE ch2.order_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES ch2.orders(id) ON DELETE RESTRICT,
    product_id uuid NOT NULL REFERENCES ch2.products(id) ON DELETE RESTRICT,
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price bigint NOT NULL CHECK (unit_price > 0),
    product_name text NOT NULL CHECK (length(btrim(product_name)) BETWEEN 1 AND 200),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT order_items_order_product_key UNIQUE (order_id, product_id)
);
CREATE INDEX order_items_product_idx ON ch2.order_items (product_id);

CREATE TABLE ch2.payments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id uuid NOT NULL REFERENCES ch2.orders(id) ON DELETE RESTRICT,
    idempotency_key uuid NOT NULL UNIQUE,
    amount bigint NOT NULL CHECK (amount > 0),
    status text NOT NULL CHECK (status IN ('succeeded', 'failed')),
    requested_success boolean NOT NULL DEFAULT true,
    failure_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT payments_failure_reason CHECK (
        (status = 'succeeded' AND failure_reason IS NULL)
        OR (status = 'failed' AND failure_reason IS NOT NULL AND length(btrim(failure_reason)) > 0)
    )
);
CREATE UNIQUE INDEX payments_one_success_per_order ON ch2.payments (order_id) WHERE status = 'succeeded';
CREATE INDEX payments_order_idx ON ch2.payments (order_id, created_at DESC);

CREATE FUNCTION ch2.set_updated_at() RETURNS trigger
LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION ch2.set_updated_at() FROM PUBLIC;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON ch2.users
    FOR EACH ROW EXECUTE FUNCTION ch2.set_updated_at();
CREATE TRIGGER products_updated_at BEFORE UPDATE ON ch2.products
    FOR EACH ROW EXECUTE FUNCTION ch2.set_updated_at();
CREATE TRIGGER orders_updated_at BEFORE UPDATE ON ch2.orders
    FOR EACH ROW EXECUTE FUNCTION ch2.set_updated_at();
CREATE TRIGGER order_items_updated_at BEFORE UPDATE ON ch2.order_items
    FOR EACH ROW EXECUTE FUNCTION ch2.set_updated_at();

-- 자체 인증을 사용하므로 브라우저에서 Supabase 테이블을 직접 읽거나 쓰지 않습니다.
-- 이후 FastAPI에서만 service_role 키를 사용하고, 모든 요청의 소유권을 확인합니다.
ALTER TABLE ch2.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE ch2.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE ch2.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE ch2.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE ch2.payments ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE ch2.users, ch2.products, ch2.orders, ch2.order_items, ch2.payments
    FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    ch2.users, ch2.products, ch2.orders, ch2.order_items, ch2.payments TO service_role;

COMMIT;
