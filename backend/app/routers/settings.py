from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AISettingsRead, AISettingsUpdate
from ..services.runtime_config import get_ai_config, list_provider_configs, save_ai_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/ai", response_model=AISettingsRead)
def read_ai_settings(db: Session = Depends(get_db)):
    config = get_ai_config(db)
    return AISettingsRead(ai_provider=config.ai_provider, providers=list_provider_configs(db))


@router.put("/ai", response_model=AISettingsRead)
def update_ai_settings(payload: AISettingsUpdate, db: Session = Depends(get_db)):
    config = save_ai_config(db, payload)
    return AISettingsRead(ai_provider=config.ai_provider, providers=list_provider_configs(db))
