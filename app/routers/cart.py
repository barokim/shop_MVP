from uuid import UUID

from fastapi import APIRouter, Depends

from app.db.client import Database, get_db
from app.schemas.orders import AddCartItemRequest, CartResponse, SetCartQuantityRequest
from app.services.auth import get_current_user
from app.services.cart import cart_action

router = APIRouter(prefix='/api/cart', tags=['장바구니'])


@router.get('', response_model=CartResponse)
def get_cart(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    return cart_action(db, user, 'get')


@router.post('/items', response_model=CartResponse)
def add_cart_item(
    data: AddCartItemRequest, user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return cart_action(db, user, 'add', data.product_id, data.quantity)


@router.patch('/items/{product_id}', response_model=CartResponse)
def set_cart_quantity(
    product_id: UUID, data: SetCartQuantityRequest,
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return cart_action(db, user, 'set', product_id, data.quantity)


@router.delete('/items/{product_id}', response_model=CartResponse)
def delete_cart_item(
    product_id: UUID, user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return cart_action(db, user, 'delete', product_id)
