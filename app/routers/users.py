from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.core.config import Settings, get_settings
from app.core.security import COOKIE_NAME
from app.db.client import Database, get_db
from app.schemas.auth import MessageResponse
from app.schemas.orders import OrderResponse
from app.schemas.users import (
    MemberResponse, PasswordChangeRequest, PasswordConfirmationRequest,
    ProfileUpdateRequest, PurchaseHistoryResponse,
)
from app.services import users
from app.services.auth import get_current_user

router = APIRouter(prefix='/api/users/me', tags=['회원정보·구매내역'])


def _clear_login_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=COOKIE_NAME, path='/', httponly=True, secure=settings.cookie_secure, samesite='lax',
    )


@router.get('', response_model=MemberResponse)
def get_profile(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    return users.get_profile(db, user)


@router.patch('', response_model=MemberResponse)
def update_profile(
    data: ProfileUpdateRequest,
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return users.update_profile(db, user, data)


@router.patch('/password', response_model=MessageResponse)
def change_password(
    data: PasswordChangeRequest, response: Response,
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    users.change_password(db, user, data)
    _clear_login_cookie(response, settings)
    return MessageResponse(message='비밀번호가 변경되었습니다. 새 비밀번호로 다시 로그인해주세요.')


@router.delete('', response_model=MessageResponse)
def delete_account(
    data: PasswordConfirmationRequest, response: Response,
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    users.delete_account(db, user, data.current_password)
    _clear_login_cookie(response, settings)
    return MessageResponse(message='회원 탈퇴가 완료되었습니다.')


@router.get('/purchases', response_model=PurchaseHistoryResponse)
def list_purchases(
    offset: int = Query(default=0, ge=0, le=2147483647),
    limit: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return users.list_purchases(db, user, offset, limit)


@router.get('/purchases/{order_id}', response_model=OrderResponse)
def get_purchase(
    order_id: UUID, user: dict = Depends(get_current_user), db: Database = Depends(get_db),
):
    return users.get_purchase(db, user, order_id)
