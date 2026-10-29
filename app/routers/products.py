from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.db.client import Database, get_db
from app.schemas.products import ProductResponse
from app.services import products

router = APIRouter(prefix='/api/products', tags=['상품'])


@router.get('', response_model=list[ProductResponse])
def list_products(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Database = Depends(get_db),
):
    return products.list_products(db, offset, limit)


@router.get('/{product_id}', response_model=ProductResponse)
def get_product(product_id: UUID, db: Database = Depends(get_db)):
    return products.get_product(db, product_id)
