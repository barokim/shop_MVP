from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: EmailStr
    password: SecretStr

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator('email')
    @classmethod
    def check_email_length(cls, value: str) -> str:
        if len(value) > 254:
            raise ValueError('이메일은 254자 이하여야 합니다.')
        return value

    @field_validator('password')
    @classmethod
    def check_password_bytes(cls, value: SecretStr) -> SecretStr:
        size = len(value.get_secret_value().encode('utf-8'))
        if not 1 <= size <= 72:
            raise ValueError('비밀번호는 UTF-8 기준 1~72바이트여야 합니다.')
        return value


class SignupRequest(Credentials):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=30)
    address: str = Field(min_length=1, max_length=500)

    @field_validator('name', 'phone', 'address', mode='before')
    @classmethod
    def strip_profile(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('password')
    @classmethod
    def check_signup_password(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 8:
            raise ValueError('비밀번호는 8자 이상이어야 합니다.')
        return value


class LoginRequest(Credentials):
    pass


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    phone: str
    address: str
    created_at: datetime


class LoginResponse(BaseModel):
    message: str = '로그인되었습니다.'
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
