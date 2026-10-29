from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.db.client import Database, get_db
from app.schemas.orders import (
    BuyNowRequest, CheckoutCartRequest, OrderResponse, PaymentRequest, PaymentResponse,
)
from app.services import orders
from app.services.auth import get_current_user

router = APIRouter(prefix='/api/orders', tags=['주문·결제'])


@router.post('/from-cart', response_model=OrderResponse)
def checkout_cart(
    data: CheckoutCartRequest,
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return orders.checkout_cart(db, user, data.cart_id)


@router.post('/buy-now', response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def buy_now(
    data: BuyNowRequest,
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return orders.buy_now(db, user, data)


@router.get('/{order_id}', response_model=OrderResponse)
def get_order(
    order_id: UUID, user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return orders.get_order(db, user, order_id)


@router.post(
    '/{order_id}/payments', response_model=PaymentResponse,
    responses={
        402: {'model': PaymentResponse, 'description': '모의 결제 실패. 결과는 DB에 저장됩니다.'},
        409: {'description': '재고 부족(결제 결과 포함), 금액 불일치, 이미 결제됨 또는 중복 키 충돌.'},
    },
)
def pay(
    order_id: UUID, data: PaymentRequest, response: Response,
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    result = orders.pay(db, user, order_id, data)
    # 실패 결과도 정상 커밋된 RPC 응답입니다. Python 예외로 결과를 유실하지 않습니다.
    response.status_code = result.pop('http_status')
    return result
