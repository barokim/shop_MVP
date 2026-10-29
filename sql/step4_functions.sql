-- STEP 4: ch2 테이블과 STEP 3 함수를 적용한 DB에 이 파일만 추가 실행합니다.
-- 테이블을 새로 만들거나 기존 데이터를 삭제하지 않습니다.
BEGIN;

DO $$
BEGIN
    IF to_regprocedure('ch2.shop_require_user(uuid,integer)') IS NULL
        OR to_regprocedure('ch2.shop_order_view(uuid)') IS NULL THEN
        RAISE EXCEPTION '먼저 sql/step3_functions.sql을 실행하세요.';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_profile(
    p_user_id uuid, p_auth_version integer,
    p_name text DEFAULT NULL, p_phone text DEFAULT NULL, p_address text DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_user ch2.users;
BEGIN
    v_user := ch2.shop_require_user(p_user_id, p_auth_version);
    IF (p_name IS NOT NULL AND length(btrim(p_name)) NOT BETWEEN 1 AND 100)
        OR (p_phone IS NOT NULL AND length(btrim(p_phone)) NOT BETWEEN 1 AND 30)
        OR (p_address IS NOT NULL AND length(btrim(p_address)) NOT BETWEEN 1 AND 500) THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
    END IF;
    IF p_name IS NOT NULL OR p_phone IS NOT NULL OR p_address IS NOT NULL THEN
        UPDATE ch2.users SET
            name = coalesce(btrim(p_name), name),
            phone = coalesce(btrim(p_phone), phone),
            address = coalesce(btrim(p_address), address)
            WHERE id = p_user_id RETURNING * INTO v_user;
    END IF;
    -- 해시, 인증 버전, 탈퇴 정보는 API 응답에 포함하지 않습니다.
    RETURN jsonb_build_object(
        'id', v_user.id, 'email', v_user.email, 'name', v_user.name,
        'phone', v_user.phone, 'address', v_user.address,
        'created_at', v_user.created_at, 'updated_at', v_user.updated_at
    );
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_change_password(
    p_user_id uuid, p_auth_version integer,
    p_expected_password_hash text, p_new_password_hash text
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_user ch2.users;
BEGIN
    v_user := ch2.shop_require_user(p_user_id, p_auth_version);
    -- Python에서 현재 비밀번호를 확인한 뒤 다른 요청이 비밀번호를 바꿨는지 재검증합니다.
    IF p_expected_password_hash IS NULL OR v_user.password_hash IS DISTINCT FROM p_expected_password_hash THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_AUTH_REQUIRED';
    END IF;
    IF p_new_password_hash IS NULL
        OR p_new_password_hash !~ '^[$]2[aby][$][0-9]{2}[$][./A-Za-z0-9]{53}$' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
    END IF;
    -- 변경과 로그인 무효화를 같은 트랜잭션에서 처리합니다.
    UPDATE ch2.users SET password_hash = p_new_password_hash, auth_version = auth_version + 1
        WHERE id = p_user_id;
    RETURN jsonb_build_object('changed', true);
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_delete_account(
    p_user_id uuid, p_auth_version integer, p_expected_password_hash text
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_user ch2.users;
BEGIN
    -- STEP 3의 결제 함수와 같은 회원 행 잠금을 사용하여 탈퇴/결제 경합을 직렬화합니다.
    v_user := ch2.shop_require_user(p_user_id, p_auth_version);
    IF p_expected_password_hash IS NULL OR v_user.password_hash IS DISTINCT FROM p_expected_password_hash THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_AUTH_REQUIRED';
    END IF;
    UPDATE ch2.users SET deleted_at = now(), auth_version = auth_version + 1 WHERE id = p_user_id;
    -- users/orders/order_items/payments 행은 삭제하지 않습니다.
    RETURN jsonb_build_object('deleted', true);
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_purchase_history(
    p_user_id uuid, p_auth_version integer, p_offset integer DEFAULT 0, p_limit integer DEFAULT 20
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
    v_items jsonb;
    v_total bigint;
BEGIN
    PERFORM ch2.shop_require_user(p_user_id, p_auth_version);
    IF p_offset IS NULL OR p_offset < 0 OR p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 100 THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_INVALID_INPUT';
    END IF;
    SELECT count(*) INTO v_total FROM ch2.orders WHERE user_id = p_user_id AND status = 'paid';
    SELECT coalesce(jsonb_agg(ch2.shop_order_view(p.id) ORDER BY p.paid_at DESC, p.id DESC), '[]'::jsonb)
        INTO v_items FROM (
            SELECT id, paid_at FROM ch2.orders WHERE user_id = p_user_id AND status = 'paid'
                ORDER BY paid_at DESC, id DESC LIMIT p_limit OFFSET p_offset
        ) p;
    RETURN jsonb_build_object('items', v_items, 'total', v_total, 'offset', p_offset, 'limit', p_limit);
END;
$$;

CREATE OR REPLACE FUNCTION ch2.shop_purchase_detail(
    p_user_id uuid, p_auth_version integer, p_order_id uuid
) RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
BEGIN
    PERFORM ch2.shop_require_user(p_user_id, p_auth_version);
    PERFORM 1 FROM ch2.orders WHERE id = p_order_id AND user_id = p_user_id AND status = 'paid';
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'SHOP_PURCHASE_NOT_FOUND';
    END IF;
    RETURN ch2.shop_order_view(p_order_id);
END;
$$;

REVOKE ALL ON FUNCTION ch2.shop_profile(uuid, integer, text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_change_password(uuid, integer, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_delete_account(uuid, integer, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_purchase_history(uuid, integer, integer, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION ch2.shop_purchase_detail(uuid, integer, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION ch2.shop_profile(uuid, integer, text, text, text),
    ch2.shop_change_password(uuid, integer, text, text), ch2.shop_delete_account(uuid, integer, text),
    ch2.shop_purchase_history(uuid, integer, integer, integer),
    ch2.shop_purchase_detail(uuid, integer, uuid) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
