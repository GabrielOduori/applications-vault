import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.models.vault import VaultConfig
from app.utils.security import (
    generate_recovery_key,
    generate_token,
    hash_passphrase,
    verify_passphrase,
)
from app.utils.filesystem import ensure_vault_dirs
from app.database import init_db


class VaultService:
    def __init__(self):
        self._active_tokens: dict[str, float] = {}  # token -> expires_at
        self._export_tokens: dict[str, float] = {}  # token -> expires_at

    def _cleanup_expired(self):
        now = time.time()
        self._active_tokens = {
            t: exp for t, exp in self._active_tokens.items() if exp > now
        }
        self._export_tokens = {
            t: exp for t, exp in self._export_tokens.items() if exp > now
        }

    @property
    def is_locked(self) -> bool:
        self._cleanup_expired()
        return len(self._active_tokens) == 0

    def is_initialized(self, db: Session | None = None) -> bool:
        if not settings.db_path.exists():
            return False
        if db is None:
            return True
        row = db.query(VaultConfig).filter_by(key="passphrase_hash").first()
        return row is not None

    def setup(self, db: Session, passphrase: str, vault_path: Path | None = None) -> dict:
        path = vault_path or settings.vault_path
        if vault_path:
            settings.vault_path = vault_path

        ensure_vault_dirs(path)
        db_file = path / "db.sqlite"
        if not db_file.exists():
            init_db(db_file)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        pass_hash = hash_passphrase(passphrase)
        recovery_key = generate_recovery_key()
        recovery_hash = hash_passphrase(recovery_key)

        configs = [
            VaultConfig(key="passphrase_hash", value=pass_hash, updated_at=now),
            VaultConfig(key="recovery_key_hash", value=recovery_hash, updated_at=now),
            VaultConfig(key="auto_lock_seconds", value=str(settings.auto_lock_seconds), updated_at=now),
            VaultConfig(key="vault_version", value="1", updated_at=now),
            VaultConfig(key="created_at", value=now, updated_at=now),
        ]
        for cfg in configs:
            db.merge(cfg)
        db.commit()

        return {
            "vault_path": str(path),
            "recovery_key": recovery_key,
            "message": "Vault created. Save your recovery key securely — it will not be shown again.",
        }

    def unlock(self, db: Session, passphrase: str | None = None, recovery_key: str | None = None, throttle_key: str = "unlock") -> dict | None:
        delay = self._get_throttle_delay(db, throttle_key)
        if delay > 0:
            return {"error": "too_many_attempts", "retry_after_seconds": delay}

        pass_row = db.query(VaultConfig).filter_by(key="passphrase_hash").first()
        if not pass_row:
            return None

        verified = False
        if passphrase:
            verified = verify_passphrase(pass_row.value, passphrase)
        elif recovery_key:
            rec_row = db.query(VaultConfig).filter_by(key="recovery_key_hash").first()
            if rec_row:
                verified = verify_passphrase(rec_row.value, recovery_key)

        if not verified:
            self._record_failed_attempt(db, throttle_key)
            return None

        self._reset_failed_attempts(db, throttle_key)
        lock_row = db.query(VaultConfig).filter_by(key="auto_lock_seconds").first()
        timeout = int(lock_row.value) if lock_row else settings.auto_lock_seconds

        token = generate_token()
        self._active_tokens[token] = time.time() + timeout

        return {"token": token, "expires_in_seconds": timeout}

    def lock(self):
        self._active_tokens.clear()
        self._export_tokens.clear()

    def validate_token(self, token: str) -> bool:
        self._cleanup_expired()
        return token in self._active_tokens

    def issue_export_token(self, db: Session, passphrase: str | None = None, recovery_key: str | None = None, throttle_key: str = "export") -> dict | None:
        # Security: require passphrase/recovery key to mint export tokens.
        # Improvement: export endpoints are not accessible with a stolen session token alone.
        delay = self._get_throttle_delay(db, throttle_key)
        if delay > 0:
            return {"error": "too_many_attempts", "retry_after_seconds": delay}

        pass_row = db.query(VaultConfig).filter_by(key="passphrase_hash").first()
        if not pass_row:
            return None

        verified = False
        if passphrase:
            verified = verify_passphrase(pass_row.value, passphrase)
        elif recovery_key:
            rec_row = db.query(VaultConfig).filter_by(key="recovery_key_hash").first()
            if rec_row:
                verified = verify_passphrase(rec_row.value, recovery_key)

        if not verified:
            self._record_failed_attempt(db, throttle_key)
            return None

        self._reset_failed_attempts(db, throttle_key)
        token = generate_token()
        self._export_tokens[token] = time.time() + settings.export_token_ttl_seconds
        return {"token": token, "expires_in_seconds": settings.export_token_ttl_seconds}

    def validate_export_token(self, token: str) -> bool:
        self._cleanup_expired()
        return token in self._export_tokens

    def reset_auto_lock_timer(self, token: str):
        if token in self._active_tokens:
            lock_seconds = settings.auto_lock_seconds
            self._active_tokens[token] = time.time() + lock_seconds

    def update_settings(self, db: Session, auto_lock_seconds: int | None = None):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if auto_lock_seconds is not None:
            row = db.query(VaultConfig).filter_by(key="auto_lock_seconds").first()
            if row:
                row.value = str(auto_lock_seconds)
                row.updated_at = now
            else:
                db.add(VaultConfig(key="auto_lock_seconds", value=str(auto_lock_seconds), updated_at=now))
            settings.auto_lock_seconds = auto_lock_seconds
            db.commit()

    def _get_throttle_delay(self, db: Session, key: str) -> float:
        # Security: throttle counters persisted in DB to survive restarts.
        # Improvement: resists brute force even if the service restarts.
        row = db.execute(
            text("SELECT failed_attempts, last_failed_at FROM auth_throttle WHERE key = :key"),
            {"key": key},
        ).fetchone()
        if not row:
            return 0
        failed_attempts = int(row[0])
        last_failed_at = float(row[1])

        if failed_attempts < 3:
            return 0
        if failed_attempts < 5:
            delay = 5.0
        elif failed_attempts < 10:
            delay = 30.0
        else:
            delay = 300.0
        elapsed = time.time() - last_failed_at
        remaining = delay - elapsed
        return max(0, remaining)

    def _record_failed_attempt(self, db: Session, key: str):
        now = time.time()
        db.execute(
            text(
                """
                INSERT INTO auth_throttle (key, failed_attempts, last_failed_at)
                VALUES (:key, 1, :now)
                ON CONFLICT(key) DO UPDATE SET
                    failed_attempts = failed_attempts + 1,
                    last_failed_at = :now
                """
            ),
            {"key": key, "now": now},
        )
        db.commit()

    def _reset_failed_attempts(self, db: Session, key: str):
        db.execute(
            text(
                """
                INSERT INTO auth_throttle (key, failed_attempts, last_failed_at)
                VALUES (:key, 0, :now)
                ON CONFLICT(key) DO UPDATE SET
                    failed_attempts = 0,
                    last_failed_at = :now
                """
            ),
            {"key": key, "now": time.time()},
        )
        db.commit()


vault_service = VaultService()
