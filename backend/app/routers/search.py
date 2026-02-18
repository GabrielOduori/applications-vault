from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import require_unlocked_vault
from app.schemas.search import SearchResponse, SearchResult
from app.services.search_service import search_fts

router = APIRouter(
    prefix="/search",
    tags=["search"],
    dependencies=[Depends(require_unlocked_vault)],
)


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    scope: str = Query("all", pattern="^(all|jobs|captures)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * per_page
    try:
        results = search_fts(q, scope=scope, limit=per_page, offset=offset)
    except ValueError as exc:
        # Security: return 400 for malformed FTS queries.
        # Improvement: avoids 500s from invalid user input.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SearchResponse(
        results=[
            SearchResult(
                job_id=r["job_id"],
                job_title=r["job_title"],
                organisation=r.get("organisation"),
                source=r["source"],
                snippet=r["snippet"],
                rank=r["rank"],
            )
            for r in results
        ],
        total=len(results),
        query=q,
    )
