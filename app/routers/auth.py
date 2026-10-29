from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.security import COOKIE_NAME, create_access_token
from app.db.client import Database, get_db
from app.schemas.auth import LoginRequest, LoginResponse, MessageResponse, SignupRequest, UserResponse
from app.services import auth

router = APIRouter(prefix='/api/auth', tags=['인증'])


@router.post('/signup', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: Database = Depends(get_db)):
    return auth.signup(data, db)


@router.post('/login', response_model=LoginResponse)
def login(
    data: LoginRequest, request: Request, response: Response,
    db: Database = Depends(get_db), settings: Settings = Depends(get_settings),
):
    user = auth.login(data, db, request.app.state.dummy_password_hash)
    token = create_access_token(user['id'], user['auth_version'], settings)
    response.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True, secure=settings.cookie_secure,
        samesite='lax', path='/', max_age=settings.access_token_expire_minutes * 60,
    )
    return LoginResponse(user=UserResponse.model_validate(user))


@router.post('/logout', response_model=MessageResponse)
def logout(
    response: Response, user: dict = Depends(auth.get_current_user),
    db: Database = Depends(get_db), settings: Settings = Depends(get_settings),
):
    auth.logout(user, db)
    response.delete_cookie(
        key=COOKIE_NAME, path='/', httponly=True,
        secure=settings.cookie_secure, samesite='lax',
    )
    return MessageResponse(message='로그아웃되었습니다. 모든 기기의 기존 로그인이 해제됩니다.')
