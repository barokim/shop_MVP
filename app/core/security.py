from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import Settings

COOKIE_NAME = 'shop_access_token'
JWT_ISSUER = 'shop-api'
JWT_AUDIENCE = 'shop-browser'


def hash_password(password: str) -> str:
    # bcrypt는 UTF-8 기준 최대 72바이트입니다. 입력 스키마에서도 검증합니다.
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('ascii')


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('ascii'))
    except (ValueError, UnicodeError):
        return False


def create_access_token(user_id: str, auth_version: int, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            'sub': user_id,
            'ver': auth_version,
            'iat': now,
            'exp': now + timedelta(minutes=settings.access_token_expire_minutes),
            'iss': JWT_ISSUER,
            'aud': JWT_AUDIENCE,
        },
        settings.secret_key.get_secret_value(),
        algorithm='HS256',
    )


def decode_access_token(token: str, settings: Settings) -> dict:
    return jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=['HS256'],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={'require': ['sub', 'ver', 'iat', 'exp', 'iss', 'aud']},
    )
