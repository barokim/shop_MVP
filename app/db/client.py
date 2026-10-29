import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException, Request, status

from app.core.config import Settings

logger = logging.getLogger('uvicorn.error')

BUSINESS_ERRORS = {
    'SHOP_AUTH_REQUIRED': (401, '다시 로그인해주세요.'),
    'SHOP_NOT_FOUND': (404, '상품, 장바구니 항목 또는 주문을 찾을 수 없습니다.'),
    'SHOP_PURCHASE_NOT_FOUND': (404, '구매내역을 찾을 수 없습니다.'),
    'SHOP_INVALID_INPUT': (422, '요청 값이 올바르지 않습니다.'),
    'SHOP_STOCK_SHORTAGE': (409, '상품 재고가 부족합니다.'),
    'SHOP_EMPTY_CART': (409, '빈 장바구니는 주문할 수 없습니다.'),
    'SHOP_AMOUNT_TOO_LARGE': (422, '주문 금액이 허용 범위를 초과합니다.'),
    'SHOP_ORDER_STATE': (409, '현재 상태에서는 결제할 수 없습니다. 주문 상태를 확인해주세요.'),
    'SHOP_AMOUNT_MISMATCH': (409, '결제 요청 금액이 주문 금액과 다릅니다.'),
    'SHOP_IDEMPOTENCY_CONFLICT': (409, '이미 사용한 결제 키의 요청 내용이 다릅니다.'),
}


class Database:
    """Supabase PostgREST를 통해 ch2에 접근하는 서버 전용 클라이언트."""

    def __init__(self, settings: Settings):
        key = settings.supabase_key.get_secret_value()
        self.client = httpx.Client(
            base_url=f'{str(settings.supabase_url).rstrip("/")}/rest/v1/',
            timeout=15.0,
            headers={
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Accept-Profile': settings.supabase_schema,
                'Content-Profile': settings.supabase_schema,
            },
        )

    def close(self) -> None:
        self.client.close()

    def _send(
        self, method: str, resource: str, *, params: dict | None = None,
        body: dict | None = None,
    ) -> Any:
        try:
            # 테이블명/컬럼명은 서버 코드의 상수이며 값은 쿼리 매개변수로 전달합니다.
            response = self.client.request(
                method, resource, params=params, json=body,
                headers={'Prefer': 'return=representation'},
            )
        except httpx.RequestError as exc:
            # URL/키/요청 본문 대신 예외 종류만 기록합니다.
            logger.warning('SUPABASE_CONNECTION_ERROR type=%s', type(exc).__name__)
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, 'DB에 연결할 수 없습니다.') from None

        if response.is_error:
            try:
                error = response.json()
                code = error.get('code')
                message = error.get('message')
            except (ValueError, AttributeError):
                code = None
                message = None
            # 오류 코드 형식만 허용하고 응답 본문/헤더/비밀키는 출력하지 않습니다.
            safe_code = code if isinstance(code, str) and re.fullmatch(r'[A-Z0-9_]{1,32}', code) else 'UNAVAILABLE'
            logger.warning(
                'SUPABASE_ERROR method=%s resource=%s status=%s code=%s',
                method, resource, response.status_code, safe_code,
            )
            if code == 'P0001' and message in BUSINESS_ERRORS:
                http_status, detail = BUSINESS_ERRORS[message]
                raise HTTPException(http_status, detail)
            if response.status_code == 409 and code == '23505':
                detail = '이미 사용 중인 이메일입니다.' if resource == 'users' else '중복 요청입니다. 주문 및 결제 키를 확인해주세요.'
                raise HTTPException(status.HTTP_409_CONFLICT, detail)
            if code in {'40001', '40P01', '55P03'}:
                raise HTTPException(status.HTTP_409_CONFLICT, '동시 요청이 충돌했습니다. 같은 요청으로 다시 시도해주세요.')
            if code == '22003':
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, '수량 또는 금액이 허용 범위를 초과합니다.')
            # 응답 본문에는 내부 DB 정보가 있을 수 있으므로 그대로 반환하지 않습니다.
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                'DB 요청에 실패했습니다. 서버 키, ch2 노출 설정, SQL 함수 및 권한을 확인하세요.',
            )
        try:
            return response.json()
        except ValueError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, 'DB 응답 형식이 올바르지 않습니다.') from None

    def request(
        self, method: str, table: str, *, params: dict | None = None,
        body: dict | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._send(method, table, params=params, body=body)
        if not isinstance(rows, list):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, 'DB 응답 형식이 올바르지 않습니다.')
        return rows

    def rpc(self, function: str, body: dict) -> dict[str, Any]:
        # 주문/결제의 여러 DB 작업은 RPC 호출 한 번의 트랜잭션 안에서 처리합니다.
        result = self._send('POST', f'rpc/{function}', body=body)
        if not isinstance(result, dict):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, 'DB 함수 응답 형식이 올바르지 않습니다.')
        return result


def get_db(request: Request) -> Database:
    return request.app.state.db
