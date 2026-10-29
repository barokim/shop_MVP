from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# PostgreSQL integer/bigint 범위를 넘는 입력은 DB 요청 전에 거절합니다.
Quantity = Annotated[int, Field(strict=True, ge=1, le=2147483647)]
Amount = Annotated[int, Field(strict=True, ge=1, le=9223372036854775807)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AddCartItemRequest(InputModel):
    product_id: UUID
    quantity: Quantity


class SetCartQuantityRequest(InputModel):
    quantity: Quantity


class CheckoutCartRequest(InputModel):
    cart_id: UUID


class BuyNowRequest(InputModel):
    product_id: UUID
    quantity: Quantity


class PaymentRequest(InputModel):
    idempotency_key: UUID
    amount: Amount
    simulate_success: bool = Field(default=True, strict=True)


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: int
    line_total: int
    stock: int


class CartResponse(BaseModel):
    id: UUID | None
    status: Literal['cart']
    is_estimate: Literal[True]
    total_amount: int
    items: list[OrderItemResponse]
    recipient_name: str | None = None
    recipient_phone: str | None = None
    shipping_address: str | None = None
    ordered_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrderResponse(BaseModel):
    id: UUID
    status: Literal['pending', 'paid']
    is_estimate: Literal[False]
    total_amount: int
    items: list[OrderItemResponse]
    recipient_name: str
    recipient_phone: str
    shipping_address: str
    ordered_at: datetime
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentResult(BaseModel):
    id: UUID
    order_id: UUID
    idempotency_key: UUID
    amount: int
    requested_success: bool
    status: Literal['succeeded', 'failed']
    failure_reason: str | None
    created_at: datetime


class PaymentResponse(BaseModel):
    replayed: bool
    payment: PaymentResult
    order: OrderResponse
