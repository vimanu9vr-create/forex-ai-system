import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
SETTINGS_FILE = Path('app/settings_store.json')


class SettingsPayload(BaseModel):
    oanda_api_key: str | None = ''
    telegram_bot_token: str | None = ''
    telegram_chat_id: str | None = ''
    risk_percentage: float | int | None = 1
    max_daily_loss: float | int | None = 3


@router.get('/settings')
def read_settings():
    if not SETTINGS_FILE.exists():
        return {
            'oanda_api_key': '',
            'telegram_bot_token': '',
            'telegram_chat_id': '',
            'risk_percentage': 1,
            'max_daily_loss': 3,
        }

    with SETTINGS_FILE.open('r', encoding='utf-8') as f:
        return json.load(f)


@router.post('/settings')
def write_settings(payload: SettingsPayload):
    data = payload.model_dump()
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    return {'saved': True, 'message': 'Settings saved successfully', 'settings': data}
