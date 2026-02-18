from pydantic import BaseModel


class VaultSetupRequest(BaseModel):
    passphrase: str
    vault_path: str | None = None


class VaultSetupResponse(BaseModel):
    vault_path: str
    recovery_key: str
    message: str


class VaultUnlockRequest(BaseModel):
    passphrase: str | None = None
    recovery_key: str | None = None


class VaultUnlockResponse(BaseModel):
    token: str
    expires_in_seconds: int


class VaultStatusResponse(BaseModel):
    initialized: bool
    locked: bool


class VaultSettingsUpdate(BaseModel):
    auto_lock_seconds: int | None = None


class VaultThrottleResponse(BaseModel):
    error: str
    retry_after_seconds: float


class VaultExportTokenRequest(BaseModel):
    passphrase: str | None = None
    recovery_key: str | None = None


class VaultExportTokenResponse(BaseModel):
    token: str
    expires_in_seconds: int
