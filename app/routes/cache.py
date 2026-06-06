from fastapi import APIRouter
from app.services.market_data import cache_status, clear_cache, _TTL_MAP
from app.services.signal_service import signal_cache_status

router = APIRouter()


@router.get("/cache/status")
def get_cache_status():
    """Show cache state for market data and signals."""
    return {
        "market_data_ttl_by_interval": _TTL_MAP,
        "market_data_cache": cache_status(),
        "signal_cache": signal_cache_status(),
    }


@router.delete("/cache/clear")
def clear_all_cache():
    clear_cache()
    return {"message": "Market data cache cleared (signals will refresh on next request)"}


@router.delete("/cache/clear/{pair}")
def clear_pair_cache(pair: str):
    clear_cache(pair.upper())
    return {"message": f"Cache cleared for {pair.upper()}"}
