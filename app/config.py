from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    public_url: str = ""
    api_token: str = "sk-super-key-change-me"
    database_url: str = "sqlite+aiosqlite:///./data/super_key.db"
    encryption_key: str = "super-key-32-byte-encryption-key!"
    admin_token: str = "admin-change-me"
    log_level: str = "INFO"
    default_admin_password: str = ""  # 默认管理员密码，必须通过环境变量设置

    model_config = {"env_prefix": "SUPER_KEY_", "env_file": ".env", "extra": "allow"}


settings = Settings()
