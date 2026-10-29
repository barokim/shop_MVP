-- STEP 3: 기존 ch2 테이블에 적용합니다. schema.sql을 다시 실행하지 마세요.
-- 전체를 SQL Editor에서 실행하며, 함수는 서버 전용 service_role만 호출합니다.
BEGIN;

-- 같은 결제 키로 모의 결과 옵션을 바꾸는 요청도 구분하기 위한 요청 스냅샷입니다.
ALTER TABLE ch2.payments ADD COLUMN IF NOT EXISTS requested_success boolean NOT NULL DEFAULT true;

CREATE OR REPLACE FUNCTION ch2.shop_require_user(p_user_id uuid, p_auth_version integer)
RETURNS ch2.users LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_user ch2.users;
BEGIN
    -- 모든 장바구니/주문/결제에서 회원 → 주문 → 상품 ID 순으로 잠급니다.
    -- 같은 회원의 동시 요청 및 로그아웃과의 경합을 직렬화합니다.
    SELECT * INTO v_user FROM ch2.users WHERE id = p_user_id FOR UPDATE;
    IF NOT FOUND OR v_user.deleted_at IS NOT NULL
        OR p_auth_version IS NULL OR v_user.auth_version <> p_auth_version THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_AUTH_REQUIRED';
    END IF;
    RETURN v_user;
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_order_view(p_order_id uuid)
RETURNS jsonb LANGUAGE sql SECURITY INVOKER SET search_path = '' AS $$
    SELECT jsonb_build_object(
        'id', o.id, 'status', o.status, 'is_estimate', o.status = 'cart',
        -- 장바구니의 표시 금액만 현재 상품 가격으로 계산합니다. DB 저장 총액은 0입니다.
        'total_amount', CASE WHEN o.status = 'cart' THEN (
            SELECT coalesce(sum(p.price::numeric * i.quantity), 0)
            FROM ch2.order_items i JOIN ch2.products p ON p.id = i.product_id
            WHERE i.order_id = o.id
        ) ELSE o.total_amount END,
        'recipient_name', o.recipient_name, 'recipient_phone', o.recipient_phone,
        'shipping_address', o.shipping_address, 'ordered_at', o.ordered_at,
        'paid_at', o.paid_at, 'created_at', o.created_at, 'updated_at', o.updated_at,
        'items', coalesce((
            SELECT jsonb_agg(jsonb_build_object(
                'id', i.id, 'product_id', i.product_id, 'quantity', i.quantity,
                'product_name', CASE WHEN o.status = 'cart' THEN p.name ELSE i.product_name END,
                'unit_price', CASE WHEN o.status = 'cart' THEN p.price ELSE i.unit_price END,
                'line_total', i.quantity::numeric * CASE WHEN o.status = 'cart' THEN p.price ELSE i.unit_price END,
                'stock', p.stock
            ) ORDER BY i.created_at, i.id)
            FROM ch2.order_items i JOIN ch2.products p ON p.id = i.product_id
            WHERE i.order_id = o.id
        ), '[]'::jsonb)
    ) FROM ch2.orders o WHERE o.id = p_order_id;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_cart(
    p_user_id uuid, p_auth_version integer, p_action text,
    p_product_id uuid DEFAULT NULL, p_quantity integer DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_cart ch2.orders;
    v_product ch2.products;
    v_existing integer;
    v_quantity bigint;
BEGIN
    PERFORM ch2.shop_require_user(p_user_id, p_auth_version);
    IF p_action IS NULL OR p_action NOT IN ('get', 'add', 'set', 'delete') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
    END IF;
    SELECT * INTO v_cart FROM ch2.orders
        WHERE user_id = p_user_id AND status = 'cart' FOR UPDATE;
    IF v_cart.id IS NULL AND p_action = 'get' THEN
        -- 조회만으로 빈 장바구니 행을 생성하지 않습니다.
        RETURN jsonb_build_object(
            'id', NULL, 'status', 'cart', 'is_estimate', true,
            'total_amount', 0, 'items', '[]'::jsonb
        );
    END IF;
    IF v_cart.id IS NULL THEN
        IF p_action <> 'add' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
        END IF;
        INSERT INTO ch2.orders (user_id) VALUES (p_user_id) RETURNING * INTO v_cart;
    END IF;
    IF p_action = 'get' THEN
        RETURN ch2.shop_order_view(v_cart.id);
    END IF;
    IF p_product_id IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
    END IF;

    IF p_action = 'delete' THEN
        DELETE FROM ch2.order_items WHERE order_id = v_cart.id AND product_id = p_product_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
        END IF;
    ELSE
        IF p_quantity IS NULL OR p_quantity <= 0 THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
        END IF;
        SELECT * INTO v_product FROM ch2.products WHERE id = p_product_id FOR UPDATE;
        IF NOT FOUND THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
        END IF;
        SELECT quantity INTO v_existing FROM ch2.order_items
            WHERE order_id = v_cart.id AND product_id = p_product_id;
        IF p_action = 'set' AND v_existing IS NULL THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
        END IF;
        v_quantity := CASE WHEN p_action = 'add'
            THEN coalesce(v_existing, 0)::bigint + p_quantity ELSE p_quantity END;
        IF v_quantity > v_product.stock THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_STOCK_SHORTAGE';
        END IF;
        INSERT INTO ch2.order_items (order_id, product_id, quantity, unit_price, product_name)
            VALUES (v_cart.id, p_product_id, v_quantity::integer, v_product.price, v_product.name)
            ON CONFLICT (order_id, product_id) DO UPDATE SET
                quantity = EXCLUDED.quantity, unit_price = EXCLUDED.unit_price,
                product_name = EXCLUDED.product_name;
    END IF;
    UPDATE ch2.orders SET updated_at = now() WHERE id = v_cart.id;
    RETURN ch2.shop_order_view(v_cart.id);
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_checkout_cart(
    p_user_id uuid, p_auth_version integer, p_cart_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_user ch2.users;
    v_order ch2.orders;
    v_item record;
    v_count integer := 0;
    v_total numeric := 0;
BEGIN
    v_user := ch2.shop_require_user(p_user_id, p_auth_version);
    SELECT * INTO v_order FROM ch2.orders
        WHERE id = p_cart_id AND user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
    END IF;
    -- 같은 cart_id의 재요청은 이미 확정한 주문을 반환하여 중복 생성을 막습니다.
    IF v_order.status IN ('pending', 'paid') THEN
        RETURN ch2.shop_order_view(v_order.id);
    END IF;
    FOR v_item IN
        SELECT i.id, i.quantity, p.price, p.name, p.stock
        FROM ch2.order_items i JOIN ch2.products p ON p.id = i.product_id
        WHERE i.order_id = v_order.id ORDER BY p.id FOR UPDATE OF p
    LOOP
        IF v_item.quantity > v_item.stock THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_STOCK_SHORTAGE';
        END IF;
        UPDATE ch2.order_items SET unit_price = v_item.price, product_name = v_item.name
            WHERE id = v_item.id;
        v_total := v_total + v_item.price::numeric * v_item.quantity;
        v_count := v_count + 1;
    END LOOP;
    IF v_count = 0 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_EMPTY_CART';
    END IF;
    IF v_total > 9223372036854775807 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_AMOUNT_TOO_LARGE';
    END IF;
    UPDATE ch2.orders SET status = 'pending', total_amount = v_total::bigint,
        recipient_name = v_user.name, recipient_phone = v_user.phone,
        shipping_address = v_user.address, ordered_at = now()
        WHERE id = v_order.id;
    RETURN ch2.shop_order_view(v_order.id);
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_buy_now(
    p_user_id uuid, p_auth_version integer, p_product_id uuid, p_quantity integer
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_user ch2.users;
    v_product ch2.products;
    v_order_id uuid;
    v_total numeric;
BEGIN
    v_user := ch2.shop_require_user(p_user_id, p_auth_version);
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
    END IF;
    SELECT * INTO v_product FROM ch2.products WHERE id = p_product_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
    END IF;
    IF p_quantity > v_product.stock THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_STOCK_SHORTAGE';
    END IF;
    v_total := v_product.price::numeric * p_quantity;
    IF v_total > 9223372036854775807 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_AMOUNT_TOO_LARGE';
    END IF;
    INSERT INTO ch2.orders (
        user_id, status, total_amount, recipient_name, recipient_phone, shipping_address, ordered_at
    ) VALUES (
        p_user_id, 'pending', v_total::bigint, v_user.name, v_user.phone, v_user.address, now()
    ) RETURNING id INTO v_order_id;
    INSERT INTO ch2.order_items (order_id, product_id, quantity, unit_price, product_name)
        VALUES (v_order_id, p_product_id, p_quantity, v_product.price, v_product.name);
    RETURN ch2.shop_order_view(v_order_id);
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_get_order(
    p_user_id uuid, p_auth_version integer, p_order_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
BEGIN
    PERFORM ch2.shop_require_user(p_user_id, p_auth_version);
    PERFORM 1 FROM ch2.orders WHERE id = p_order_id AND user_id = p_user_id AND status <> 'cart';
    IF NOT FOUND THEN
        -- 다른 회원의 주문과 존재하지 않는 주문은 동일한 404로 처리합니다.
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
    END IF;
    RETURN ch2.shop_order_view(p_order_id);
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_pay(
    p_user_id uuid, p_auth_version integer, p_order_id uuid,
    p_idempotency_key uuid, p_amount bigint, p_simulate_success boolean
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_order ch2.orders;
    v_payment ch2.payments;
    v_item record;
    v_shortage boolean := false;
    v_total numeric;
    v_reason text;
    v_status text;
    v_http_status integer;
BEGIN
    PERFORM ch2.shop_require_user(p_user_id, p_auth_version);
    IF p_idempotency_key IS NULL OR p_amount IS NULL OR p_amount <= 0 OR p_simulate_success IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
    END IF;
    SELECT * INTO v_order FROM ch2.orders
        WHERE id = p_order_id AND user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_NOT_FOUND';
    END IF;
    SELECT * INTO v_payment FROM ch2.payments WHERE idempotency_key = p_idempotency_key;
    IF FOUND THEN
        IF v_payment.order_id <> p_order_id OR v_payment.amount <> p_amount
            OR v_payment.requested_success <> p_simulate_success THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_IDEMPOTENCY_CONFLICT';
        END IF;
        -- 실패한 요청의 재전송도 처음 결과를 그대로 반환합니다. 재시도에는 새 키가 필요합니다.
        v_http_status := CASE WHEN v_payment.status = 'succeeded' THEN 200
            WHEN v_payment.failure_reason = '재고 부족' THEN 409 ELSE 402 END;
        RETURN jsonb_build_object(
            'http_status', v_http_status, 'replayed', true,
            'payment', to_jsonb(v_payment), 'order', ch2.shop_order_view(p_order_id)
        );
    END IF;
    IF v_order.status <> 'pending' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_ORDER_STATE';
    END IF;
    IF p_amount <> v_order.total_amount THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_AMOUNT_MISMATCH';
    END IF;
    SELECT sum(unit_price::numeric * quantity) INTO v_total
        FROM ch2.order_items WHERE order_id = p_order_id;
    IF v_total IS NULL OR v_total <> v_order.total_amount THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_ORDER_STATE';
    END IF;

    -- 여러 상품을 항상 동일한 순서로 잠가 동시 결제 시 교착 가능성을 줄입니다.
    FOR v_item IN
        SELECT p.id, p.stock, i.quantity FROM ch2.order_items i
        JOIN ch2.products p ON p.id = i.product_id
        WHERE i.order_id = p_order_id ORDER BY p.id FOR UPDATE OF p
    LOOP
        IF v_item.quantity > v_item.stock THEN
            v_shortage := true;
        END IF;
    END LOOP;
    IF v_shortage THEN
        v_status := 'failed'; v_reason := '재고 부족'; v_http_status := 409;
    ELSIF NOT p_simulate_success THEN
        v_status := 'failed'; v_reason := '모의 결제 실패'; v_http_status := 402;
    ELSE
        v_status := 'succeeded'; v_reason := NULL; v_http_status := 200;
    END IF;

    INSERT INTO ch2.payments (order_id, idempotency_key, amount, status, failure_reason, requested_success)
        VALUES (p_order_id, p_idempotency_key, v_order.total_amount, v_status, v_reason, p_simulate_success)
        RETURNING * INTO v_payment;
    IF v_status = 'succeeded' THEN
        UPDATE ch2.products p SET stock = p.stock - i.quantity
            FROM ch2.order_items i WHERE i.order_id = p_order_id AND i.product_id = p.id;
        UPDATE ch2.orders SET status = 'paid', paid_at = now() WHERE id = p_order_id;
    END IF;
    -- 실패는 예외를 던지지 않아야 결과 행이 롤백되지 않습니다. HTTP 상태는 서버가 반영합니다.
    RETURN jsonb_build_object(
        'http_status', v_http_status, 'replayed', false,
        'payment', to_jsonb(v_payment), 'order', ch2.shop_order_view(p_order_id)
    );
END;
$$;

REVOKE ALL ON FUNCTION ch2.shop_require_user(uuid, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_order_view(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_cart(uuid, integer, text, uuid, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_checkout_cart(uuid, integer, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_buy_now(uuid, integer, uuid, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_get_order(uuid, integer, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_pay(uuid, integer, uuid, uuid, bigint, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION ch2.shop_require_user(uuid, integer), ch2.shop_order_view(uuid),
    ch2.shop_cart(uuid, integer, text, uuid, integer), ch2.shop_checkout_cart(uuid, integer, uuid),
    ch2.shop_buy_now(uuid, integer, uuid, integer), ch2.shop_get_order(uuid, integer, uuid),
    ch2.shop_pay(uuid, integer, uuid, uuid, bigint, boolean) TO service_role;

-- PostgREST가 새 RPC 함수를 인식하도록 스키마 캐시를 갱신합니다.
NOTIFY pgrst, 'reload schema';
COMMIT;
