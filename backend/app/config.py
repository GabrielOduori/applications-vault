from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vault_path: Path = Path.home() / "ApplicationVault"
    auto_lock_seconds: int = 900  # 15 minutes
    # Security: cap upload and capture sizes to reduce memory/disk DoS risk.
    # Improvement: rejects oversized payloads before heavy processing.
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MiB
    max_html_content_chars: int = 200_000
    max_text_snapshot_chars: int = 200_000
    # Security: require a short-lived export token (separate from session token).
    # Improvement: stolen session tokens alone cannot export vault data.
    export_token_ttl_seconds: int = 60
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def db_path(self) -> Path:
        return self.vault_path / "db.sqlite"

    @property
    def jobs_dir(self) -> Path:
        return self.vault_path / "jobs"

    model_config = {"env_prefix": "VAULT_"}


settings = Settings()
