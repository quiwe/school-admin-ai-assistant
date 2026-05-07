from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import AIModelListRequest, AIModelListResponse, AISettingsRead, AISettingsUpdate
from ..services.model_discovery import ModelDiscoveryError, discover_models
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


@router.post("/ai/models", response_model=AIModelListResponse)
def list_ai_models(payload: AIModelListRequest, db: Session = Depends(get_db)):
    try:
        models = discover_models(db, payload.provider_id, payload.api_key, payload.base_url)
    except ModelDiscoveryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AIModelListResponse(models=models, source=payload.provider_id)
