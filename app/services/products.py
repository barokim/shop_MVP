from uuid import UUID

from fastapi import HTTPException, status

from app.db.client import Database

PRODUCT_COLUMNS = 'id,sku,name,description,price,stock,created_at,updated_at'


def list_products(db: Database, offset: int, limit: int) -> list[dict]:
    return db.request('GET', 'products', params={
        'select': PRODUCT_COLUMNS, 'order': 'created_at.desc,id.asc',
        'offset': str(offset), 'limit': str(limit),
    })


def get_product(db: Database, product_id: UUID) -> dict:
    rows = db.request('GET', 'products', params={
        'select': PRODUCT_COLUMNS, 'id': f'eq.{product_id}', 'limit': '1',
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, '상품을 찾을 수 없습니다.')
    return rows[0]
