from uuid import UUID

from app.db.client import Database
from app.schemas.orders import BuyNowRequest, PaymentRequest


def actor(user: dict) -> dict:
    return {'p_user_id': str(user['id']), 'p_auth_version': user['auth_version']}


def checkout_cart(db: Database, user: dict, cart_id: UUID) -> dict:
    return db.rpc('shop_checkout_cart', {**actor(user), 'p_cart_id': str(cart_id)})


def buy_now(db: Database, user: dict, data: BuyNowRequest) -> dict:
    return db.rpc('shop_buy_now', {
        **actor(user), 'p_product_id': str(data.product_id), 'p_quantity': data.quantity,
    })


def get_order(db: Database, user: dict, order_id: UUID) -> dict:
    return db.rpc('shop_get_order', {**actor(user), 'p_order_id': str(order_id)})


def pay(db: Database, user: dict, order_id: UUID, data: PaymentRequest) -> dict:
    return db.rpc('shop_pay', {
        **actor(user), 'p_order_id': str(order_id),
        'p_idempotency_key': str(data.idempotency_key),
        'p_amount': data.amount, 'p_simulate_success': data.simulate_success,
    })
