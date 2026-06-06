from fastapi import APIRouter

from app.routes.bos import bos
from app.routes.choch import choch
from app.routes.crew import crew_analysis
from app.routes.sessions import sessions_analysis
from app.routes.sweeps import sweeps

router = APIRouter()


def _safe_call(fn, key):
    try:
        data = fn()
        return data.get(key), None
    except Exception as exc:
        return None, str(exc)


@router.get('/ai-analysis')
def ai_analysis():
    crew_data, crew_err = _safe_call(crew_analysis, 'analysis')
    bos_data, bos_err = _safe_call(bos, 'bos')
    choch_data, choch_err = _safe_call(choch, 'choch')
    sweeps_data, sweeps_err = _safe_call(sweeps, 'sweeps')
    session_data, session_err = _safe_call(sessions_analysis, 'session')

    crew_full = {}
    try:
        crew_full = crew_analysis()
    except Exception:
        crew_full = {}

    warning_parts = [
        part for part in [
            f"crew: {crew_err}" if crew_err else None,
            f"bos: {bos_err}" if bos_err else None,
            f"choch: {choch_err}" if choch_err else None,
            f"sweeps: {sweeps_err}" if sweeps_err else None,
            f"sessions: {session_err}" if session_err else None,
        ] if part
    ]

    return {
        'bos_analysis': str(bos_data) if bos_data is not None else 'BOS data unavailable',
        'choch_analysis': str(choch_data) if choch_data is not None else 'CHOCH data unavailable',
        'liquidity_sweeps': str(sweeps_data) if sweeps_data is not None else 'Liquidity sweeps unavailable',
        'session_analysis': str(session_data) if session_data is not None else 'Session analysis unavailable',
        'ai_probability': crew_full.get('signal', {}).get('probability'),
        'analysis': crew_data,
        'source': crew_full.get('source', 'ai-analysis'),
        'warning': '; '.join(warning_parts) if warning_parts else crew_full.get('warning'),
    }
