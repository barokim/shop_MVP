from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.schemas.auth import UserResponse
from app.schemas.orders import OrderResponse


class MemberResponse(UserResponse):
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=1, max_length=30)
    address: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator('name', 'phone', 'address', mode='before')
    @classmethod
    def strip_and_reject_null(cls, value):
        # 생략한 필드는 유지하고, 명시적인 null/공백으로 정보를 지우는 요청은 거절합니다.
        if value is None:
            raise ValueError('수정할 항목에는 null을 사용할 수 없습니다.')
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode='after')
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError('이름, 연락처, 주소 중 하나 이상을 입력하세요.')
        return self


def validate_password_bytes(value: SecretStr) -> SecretStr:
    if not 1 <= len(value.get_secret_value().encode('utf-8')) <= 72:
        raise ValueError('비밀번호는 UTF-8 기준 1~72바이트여야 합니다.')
    return value


class PasswordConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    current_password: SecretStr

    @field_validator('current_password')
    @classmethod
    def check_current_password(cls, value: SecretStr) -> SecretStr:
        return validate_password_bytes(value)


class PasswordChangeRequest(PasswordConfirmationRequest):
    new_password: SecretStr

    @field_validator('new_password')
    @classmethod
    def check_new_password(cls, value: SecretStr) -> SecretStr:
        validate_password_bytes(value)
        if len(value.get_secret_value()) < 8:
            raise ValueError('새 비밀번호는 8자 이상이어야 합니다.')
        return value


class PurchaseHistoryResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    offset: int
    limit: int
