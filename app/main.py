import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import PROJECT_ROOT, get_settings
from app.core.security import COOKIE_NAME, hash_password
from app.db.client import Database
from app.routers.auth import router as auth_router
from app.routers.cart import router as cart_router
from app.routers.orders import router as orders_router
from app.routers.pages import router as pages_router
from app.routers.products import router as products_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.db = Database(settings)
    app.state.dummy_password_hash = hash_password(secrets.token_urlsafe(24))
    try:
        yield
    finally:
        app.state.db.close()


app = FastAPI(title='AI-Marine Shop API', version='0.5.0', lifespan=lifespan)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(users_router)
app.include_router(pages_router)
app.mount('/static', StaticFiles(directory=PROJECT_ROOT / 'static'), name='static')


@app.middleware('http')
async def protect_requests(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        allowed = str(request.app.state.settings.app_origin).rstrip('/')
        # 다른 출처의 로그인 요청도 차단합니다. 쿠키 변경 요청에는 Origin이 필수입니다.
        if (origin is not None and origin != allowed) or (COOKIE_NAME in request.cookies and origin is None):
            return JSONResponse(status_code=403, content={'detail': '허용되지 않은 요청 출처입니다.'})
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # 기본 검증 응답의 input 필드에 원문 비밀번호가 포함되지 않도록 제거합니다.
    errors = [{'loc': list(error['loc']), 'msg': error['msg'], 'type': error['type']} for error in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': errors})
