import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    AIModelListRequest,
    AIModelListResponse,
    AIProviderTestRequest,
    AIProviderTestResponse,
    AISettingsRead,
    AISettingsUpdate,
)
from ..services.ai_provider import ai_provider
from ..services.model_discovery import ModelDiscoveryError, discover_models
from ..services.runtime_config import (
    AIConfig,
    PROVIDER_MAP,
    get_ai_config,
    get_provider_api_key,
    get_provider_base_url,
    get_provider_model,
    list_provider_configs,
    normalize_provider_id,
    save_ai_config,
)

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


@router.post("/ai/test", response_model=AIProviderTestResponse)
def test_ai_provider(payload: AIProviderTestRequest, db: Session = Depends(get_db)):
    provider_id = normalize_provider_id(payload.provider_id)
    preset = PROVIDER_MAP[provider_id]
    config = AIConfig(
        ai_provider=provider_id,
        provider_type=preset.provider_type,
        api_key=(payload.api_key or "").strip() or get_provider_api_key(db, provider_id),
        model=(payload.model or "").strip() or get_provider_model(db, preset),
        base_url=(payload.base_url or "").strip() or get_provider_base_url(db, preset),
    )
    started = time.perf_counter()
    try:
        text = ai_provider._chat("请回复“连接测试成功”，不要输出其他内容。", config)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        raise HTTPException(status_code=400, detail=f"模型测试失败：{exc}，耗时 {latency_ms} ms") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)
    return AIProviderTestResponse(
        ok=True,
        message="模型连接测试成功",
        latency_ms=latency_ms,
        preview=text.strip()[:120],
    )
