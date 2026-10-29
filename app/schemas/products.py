from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: UUID
    sku: str
    name: str
    description: str
    price: int
    stock: int
    created_at: datetime
    updated_at: datetime
