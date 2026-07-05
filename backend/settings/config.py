from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PETMALL_",
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PetMall"
    env: str = "local"
    debug: bool = True

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    public_h5_url: str = "http://127.0.0.1:8080"
    cors_origins: str = "http://127.0.0.1:8080,http://localhost:8080"

    mysql_db_uri: str = "mysql+aiomysql://root:change_me@127.0.0.1:3306/petmall?charset=utf8mb4"
    redis_url: str = "redis://127.0.0.1:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@127.0.0.1:5672/"

    jwt_secret_key: str = "change_me_in_local_env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    generated_asset_dir: str = "generated"
    vector_store_dir: str = "generated/vector_store"
    max_upload_size_mb: int = 20

    payment_mode: str = "mock"
    mock_payment_enabled: bool = True

    aliyun_sms_access_key_id: str = Field(default="")
    aliyun_sms_access_key_secret: str = Field(default="")
    aliyun_sms_sign_name: str = Field(default="")
    aliyun_sms_template_code: str = "100001"
    aliyun_sms_endpoint: str = "dypnsapi.aliyuncs.com"
    sms_code_expire_seconds: int = 300
    sms_send_cooldown_seconds: int = 60
    sms_debug_code_enabled: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def generated_asset_path(self) -> Path:
        path = Path(self.generated_asset_dir)
        if path.is_absolute():
            return path
        return BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
