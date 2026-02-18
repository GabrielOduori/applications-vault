from fastapi import Header, HTTPException

from app.services.vault_service import vault_service


async def require_unlocked_vault(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization[7:]
    if not vault_service.validate_token(token):
        raise HTTPException(status_code=401, detail="Vault is locked or token expired")
    vault_service.reset_auto_lock_timer(token)
    return token


async def require_export_token(x_vault_export_token: str = Header(...)):
    # Security: protect export endpoints with a short-lived export token.
    # Improvement: reduces risk of data exfiltration from stolen session tokens.
    if not vault_service.validate_export_token(x_vault_export_token):
        raise HTTPException(status_code=401, detail="Invalid or expired export token")
    return x_vault_export_token
