"""应用配置：全部来自环境变量（.env），禁止在代码中硬编码任何凭据。

配置体系遵循《01-设计原则与约束》：连接凭据仅存环境变量，
业务可配置项（钉钉配置）存 sys_config 表。
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置模型（pydantic-settings 从 .env / 环境变量读取）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 服务 =====
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "data/contracts"  # 逗号分隔的前端域名白名单

    # ===== 初始超管（首次启动幂等创建；该初始密码仅用于首次登录，登录后强制改密）=====
    admin_username: str = "admin"
    admin_password: str = "123456"

    # ===== JWT =====
    jwt_secret: str = "please-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ===== 加密主密钥（Fernet，生产环境必须替换）=====
    fernet_key: str = "please-change-me"

    # ===== 数据源连接（聚合格式，必填；见《02》4.6）=====
    database_url: str  # 例如 postgresql+asyncpg://app_user:密码@host:5432/contract_risk
    redis_url: str     # 例如 redis://:密码@host:6379/0

    # ===== 连接池（SQLAlchemy async + asyncpg / Redis，见《02》4.6 /《09》第 2 节）=====
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True
    db_echo: bool = False
    redis_max_connections: int = 50

    # ===== 钉钉（初始值；运行时以 sys_config 中超管配置为准）=====
    dingtalk_client_id: str = ""
    dingtalk_client_secret: str = ""
    dingtalk_redirect_uri: str = "http://localhost:5173/dingtalk/callback"


@lru_cache
def get_settings() -> Settings:
    """返回全局配置单例（lru_cache 保证只加载一次）。"""
    return Settings()