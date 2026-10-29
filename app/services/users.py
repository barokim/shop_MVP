from uuid import UUID

from fastapi import HTTPException, status
from pydantic import SecretStr

from app.core.security import hash_password, verify_password
from app.db.client import Database
from app.schemas.users import PasswordChangeRequest, ProfileUpdateRequest
from app.services.orders import actor


def get_profile(db: Database, user: dict) -> dict:
    return db.rpc('shop_profile', actor(user))


def update_profile(db: Database, user: dict, data: ProfileUpdateRequest) -> dict:
    changes = {f'p_{key}': value for key, value in data.model_dump(exclude_unset=True).items()}
    return db.rpc('shop_profile', {**actor(user), **changes})


def _confirm_password(db: Database, user: dict, password: SecretStr) -> str:
    rows = db.request('GET', 'users', params={
        'select': 'password_hash', 'id': f'eq.{user["id"]}',
        'auth_version': f'eq.{user["auth_version"]}', 'deleted_at': 'is.null', 'limit': '1',
    })
    if not rows:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, '다시 로그인해주세요.')
    saved_hash = rows[0]['password_hash']
    if not verify_password(password.get_secret_value(), saved_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, '현재 비밀번호가 올바르지 않습니다.')
    return saved_hash


def change_password(db: Database, user: dict, data: PasswordChangeRequest) -> None:
    expected_hash = _confirm_password(db, user, data.current_password)
    # 느린 bcrypt 연산은 DB 잠금 전에 수행하고, 실제 저장 시 검증한 해시와 버전을 다시 확인합니다.
    new_hash = hash_password(data.new_password.get_secret_value())
    db.rpc('shop_change_password', {
        **actor(user), 'p_expected_password_hash': expected_hash, 'p_new_password_hash': new_hash,
    })


def delete_account(db: Database, user: dict, current_password: SecretStr) -> None:
    expected_hash = _confirm_password(db, user, current_password)
    db.rpc('shop_delete_account', {**actor(user), 'p_expected_password_hash': expected_hash})


def list_purchases(db: Database, user: dict, offset: int, limit: int) -> dict:
    return db.rpc('shop_purchase_history', {**actor(user), 'p_offset': offset, 'p_limit': limit})


def get_purchase(db: Database, user: dict, order_id: UUID) -> dict:
    return db.rpc('shop_purchase_detail', {**actor(user), 'p_order_id': str(order_id)})
