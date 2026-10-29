from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / '.env', env_file_encoding='utf-8', extra='ignore'
    )

    supabase_url: AnyHttpUrl
    supabase_key: SecretStr
    supabase_schema: str = 'ch2'
    secret_key: SecretStr
    app_origin: AnyHttpUrl = 'http://127.0.0.1:8000'
    cookie_secure: bool = False
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)

    @field_validator('secret_key')
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32 or secret.startswith('REPLACE_'):
            raise ValueError('SECRET_KEY를 32자 이상의 무작위 비밀값으로 설정하세요.')
        return value

    @field_validator('supabase_key')
    @classmethod
    def validate_supabase_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value() or value.get_secret_value().startswith('REPLACE_'):
            raise ValueError('SUPABASE_KEY에 서버 전용 service_role 키를 설정하세요.')
        return value

    @field_validator('supabase_schema')
    @classmethod
    def validate_schema(cls, value: str) -> str:
        if value != 'ch2':
            raise ValueError('현재 프로젝트의 DB 스키마는 ch2입니다.')
        return value

    @field_validator('app_origin')
    @classmethod
    def validate_origin(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.path not in (None, '', '/') or value.query or value.fragment or value.username or value.password:
            raise ValueError('APP_ORIGIN은 경로 없는 웹 주소여야 합니다.')
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
