from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import PROJECT_ROOT

router = APIRouter(include_in_schema=False)


def html_page(filename: str) -> FileResponse:
    # 파일명은 고정된 서버 코드에서만 전달하며 사용자 경로를 파일 경로로 사용하지 않습니다.
    return FileResponse(
        PROJECT_ROOT / 'templates' / filename,
        media_type='text/html', headers={'Cache-Control': 'no-store'},
    )


@router.get('/')
def home():
    return RedirectResponse('/products', status_code=303)


@router.get('/products')
def products():
    return html_page('products.html')


@router.get('/products/{product_id}')
def product_detail(product_id: UUID):
    return html_page('product-detail.html')


@router.get('/login')
def login():
    return html_page('login.html')


@router.get('/signup')
def signup():
    return html_page('signup.html')


@router.get('/cart')
def cart():
    return html_page('cart.html')


@router.get('/payment')
def payment():
    return html_page('payment.html')


@router.get('/account')
def account():
    return html_page('account.html')


@router.get('/purchases')
def purchases():
    return html_page('purchases.html')
