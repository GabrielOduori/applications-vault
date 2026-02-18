from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse

from app.dependencies import require_unlocked_vault, require_export_token
from app.services.backup_service import export_vault_zip, export_csv, export_json

# Security: exports require both session token and short-lived export token.
# Improvement: reduces blast radius of stolen session tokens.
router = APIRouter(tags=["backup"], dependencies=[Depends(require_unlocked_vault), Depends(require_export_token)])


@router.post("/backup/export")
async def backup_export():
    buf = export_vault_zip()
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="application_vault_backup.zip"'},
    )


@router.get("/export/csv")
async def csv_export():
    csv_data = export_csv()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="jobs_export.csv"'},
    )


@router.get("/export/json")
async def json_export():
    data = export_json()
    return data
