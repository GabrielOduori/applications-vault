from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_unlocked_vault
from app.schemas.vault import (
    VaultSetupRequest,
    VaultSetupResponse,
    VaultStatusResponse,
    VaultSettingsUpdate,
    VaultUnlockRequest,
    VaultUnlockResponse,
    VaultThrottleResponse,
    VaultExportTokenRequest,
    VaultExportTokenResponse,
)
from app.services.vault_service import vault_service

router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("/status", response_model=VaultStatusResponse)
async def vault_status(db: Session = Depends(get_db)):
    return VaultStatusResponse(
        initialized=vault_service.is_initialized(db),
        locked=vault_service.is_locked,
    )


@router.post("/setup", response_model=VaultSetupResponse)
async def vault_setup(req: VaultSetupRequest, db: Session = Depends(get_db)):
    if vault_service.is_initialized(db):
        raise HTTPException(status_code=409, detail="Vault already initialized")
    if len(req.passphrase) < 8:
        raise HTTPException(status_code=400, detail="Passphrase must be at least 8 characters")

    vault_path = None
    if req.vault_path:
        candidate = Path(req.vault_path).expanduser().resolve()
        vault_path = candidate
    result = vault_service.setup(db, req.passphrase, vault_path)
    return VaultSetupResponse(**result)


@router.post("/unlock", response_model=VaultUnlockResponse | VaultThrottleResponse)
async def vault_unlock(req: VaultUnlockRequest, request: Request, db: Session = Depends(get_db)):
    if not vault_service.is_initialized(db):
        raise HTTPException(status_code=404, detail="Vault not initialized")
    if not req.passphrase and not req.recovery_key:
        raise HTTPException(status_code=400, detail="Provide passphrase or recovery_key")

    client_host = request.client.host if request.client else "unknown"
    # Security: throttle by client host to slow brute force attempts.
    # Improvement: persistent rate limits survive restarts.
    result = vault_service.unlock(db, req.passphrase, req.recovery_key, throttle_key=f"unlock:{client_host}")
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid passphrase or recovery key")
    if "error" in result:
        raise HTTPException(status_code=429, detail=result)
    return VaultUnlockResponse(**result)


@router.post("/export-token", response_model=VaultExportTokenResponse | VaultThrottleResponse)
async def vault_export_token(req: VaultExportTokenRequest, request: Request, db: Session = Depends(get_db)):
    # Security: require passphrase or recovery key to obtain short-lived export token.
    # Improvement: backup/export endpoints are gated behind explicit re-auth.
    if not vault_service.is_initialized(db):
        raise HTTPException(status_code=404, detail="Vault not initialized")
    if not req.passphrase and not req.recovery_key:
        raise HTTPException(status_code=400, detail="Provide passphrase or recovery_key")

    client_host = request.client.host if request.client else "unknown"
    # Security: throttle export-token issuance by client host.
    # Improvement: slows repeated export-token attempts across restarts.
    result = vault_service.issue_export_token(db, req.passphrase, req.recovery_key, throttle_key=f"export:{client_host}")
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid passphrase or recovery key")
    if "error" in result:
        raise HTTPException(status_code=429, detail=result)
    return VaultExportTokenResponse(**result)


@router.post("/lock")
async def vault_lock(_token: str = Depends(require_unlocked_vault)):
    vault_service.lock()
    return {"message": "Vault locked"}


@router.put("/settings")
async def vault_settings(
    req: VaultSettingsUpdate,
    _token: str = Depends(require_unlocked_vault),
    db: Session = Depends(get_db),
):
    vault_service.update_settings(db, auto_lock_seconds=req.auto_lock_seconds)
    return {"message": "Settings updated"}
