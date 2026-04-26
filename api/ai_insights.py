import traceback
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from services.ai_insight_service import generate_ai_spending_insight
from services.cache import ai_insight_cache

router = APIRouter(prefix="/ai", tags=["AI Insights"])


@router.get("/spending-insight")
async def api_spending_insight(
    customer_id: str = Query(...),
    bank_id: Optional[str] = Query(None),
):
    cache_key = (customer_id, bank_id or "")
    cached = ai_insight_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        result = await generate_ai_spending_insight(customer_id, bank_id)
        ai_insight_cache[cache_key] = result
        return result
    except Exception as e:
        print("AI spending insight route error:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))