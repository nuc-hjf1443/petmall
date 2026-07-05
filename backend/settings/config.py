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
    vector_store_dir: str = "generated/private/vector_store"
    max_upload_size_mb: int = 20

    payment_mode: str = "mock"
    mock_payment_enabled: bool = True
    alipay_gateway_url: str = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
    alipay_app_id: str = ""
    alipay_private_key: str = ""
    alipay_public_key: str = ""
    alipay_seller_id: str = ""
    alipay_notify_url: str = "http://127.0.0.1:8000/payments/alipay/notify"
    alipay_return_url: str = "http://127.0.0.1:8000/payments/alipay/return"

    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 100
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embed_model: str = "nomic-embed-text"
    chroma_collection: str = "petmall_knowledge"
    knowledge_task_lease_seconds: int = 900

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

    @property
    def public_asset_path(self) -> Path:
        return self.generated_asset_path / "public"

    @property
    def private_asset_path(self) -> Path:
        return self.generated_asset_path / "private"

    @property
    def vector_store_path(self) -> Path:
        path = Path(self.vector_store_dir)
        if path.is_absolute():
            return path
        return BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
