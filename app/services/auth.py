from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.security import COOKIE_NAME, decode_access_token, hash_password, verify_password
from app.db.client import Database, get_db
from app.schemas.auth import LoginRequest, SignupRequest

USER_COLUMNS = 'id,email,name,phone,address,created_at,auth_version,deleted_at'


def signup(data: SignupRequest, db: Database) -> dict:
    # 이메일 중복은 DB UNIQUE 제약으로 동시 가입 요청까지 방지합니다.
    rows = db.request('POST', 'users', params={'select': USER_COLUMNS}, body={
        'email': str(data.email),
        'password_hash': hash_password(data.password.get_secret_value()),
        'name': data.name, 'phone': data.phone, 'address': data.address,
    })
    if not rows:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, '가입 결과를 확인할 수 없습니다.')
    return rows[0]


def login(data: LoginRequest, db: Database, dummy_hash: str) -> dict:
    rows = db.request('GET', 'users', params={
        'select': f'{USER_COLUMNS},password_hash', 'email': f'eq.{data.email}', 'limit': '1',
    })
    user = rows[0] if rows else None
    # 없는 이메일도 해시 검사를 수행하여 응답 시간 차이를 줄입니다.
    valid = verify_password(
        data.password.get_secret_value(), user['password_hash'] if user else dummy_hash
    )
    if not user or not valid or user['deleted_at'] is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, '이메일 또는 비밀번호가 올바르지 않습니다.')
    return user


def get_current_user(
    request: Request, db: Database = Depends(get_db), settings: Settings = Depends(get_settings),
) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, '로그인이 필요합니다.')
    try:
        payload = decode_access_token(token, settings)
        user_id = str(UUID(payload['sub']))
        version = payload['ver']
        if type(version) is not int:
            raise ValueError('invalid version')
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, '로그인이 만료되었거나 유효하지 않습니다.') from None

    rows = db.request('GET', 'users', params={
        'select': USER_COLUMNS, 'id': f'eq.{user_id}', 'limit': '1',
    })
    if not rows or rows[0]['deleted_at'] is not None or rows[0]['auth_version'] != version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, '다시 로그인해주세요.')
    return rows[0]


def logout(user: dict, db: Database) -> None:
    # 비교 조건을 함께 보내 동시 로그아웃의 버전 덮어쓰기를 막습니다.
    db.request('PATCH', 'users', params={
        'id': f'eq.{user["id"]}', 'auth_version': f'eq.{user["auth_version"]}', 'select': 'id',
    }, body={'auth_version': user['auth_version'] + 1})
