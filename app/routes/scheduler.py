from fastapi import APIRouter
from app.services.signal_scheduler import start_signal_scheduler, stop_signal_scheduler, get_scheduler

router = APIRouter()

@router.get("/scheduler/start")
def start_scheduler():
    """Start the 5-minute signal refresh scheduler."""
    try:
        scheduler = start_signal_scheduler()
        return {
            "status": "started",
            "message": "Signal scheduler started (5-minute refresh cycle)",
            "interval_seconds": scheduler.interval_seconds,
            "filters": {
                "min_confidence": "80%",
                "multi_timeframe_alignment": "required",
                "min_rr_ratio": "1.5",
                "duplicate_prevention": "enabled"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/scheduler/stop")
def stop_scheduler():
    """Stop the signal refresh scheduler."""
    try:
        stop_signal_scheduler()
        return {
            "status": "stopped",
            "message": "Signal scheduler stopped"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/scheduler/status")
def scheduler_status():
    """Get current scheduler status."""
    scheduler = get_scheduler()
    return {
        "running": scheduler.running,
        "interval_seconds": scheduler.interval_seconds,
        "interval_minutes": scheduler.interval_seconds / 60,
        "filters_active": {
            "min_confidence": "80%",
            "multi_timeframe_alignment": True,
            "min_rr_ratio": "1.5",
            "duplicate_alert_prevention": True,
            "high_profitability_only": True
        },
        "message": "Scheduler is actively refreshing signals every 5 minutes and filtering for high-confidence, profitable setups."
    }

@router.get("/scheduler/config")
def scheduler_config():
    """Get scheduler configuration details."""
    return {
        "refresh_interval": "5 minutes",
        "filters": [
            {
                "name": "Confidence Filter",
                "threshold": "80%",
                "description": "Only setups with >= 80% confidence are considered"
            },
            {
                "name": "Multi-timeframe Alignment",
                "requirement": "Must be aligned",
                "description": "Higher timeframe bias must align with lower timeframe setup"
            },
            {
                "name": "Profitability Filter",
                "threshold": "RR >= 1.5",
                "description": "Risk/Reward ratio must be at least 1:1.5"
            },
            {
                "name": "Duplicate Prevention",
                "status": "Enabled",
                "description": "Same pair is not alerted twice in same 5-min cycle"
            }
        ],
        "alert_destination": "Telegram",
        "alert_format": "Full setup details with timeframe and multi-timeframe confirmation"
    }
