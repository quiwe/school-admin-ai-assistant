import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReplyHistory, Setting
from ..schemas import (
    AIModelListRequest,
    AIModelListResponse,
    AIProviderTestRequest,
    AIProviderTestResponse,
    AISettingsRead,
    AISettingsUpdate,
    AutoStartSettingsRead,
    AutoStartSettingsUpdate,
    BudgetRequest,
    CostStatsResponse,
    QQSettingsRead,
    QQSettingsUpdate,
    WeComSettingsRead,
    WeComSettingsUpdate,
)
from ..services.autostart import get_status as get_autostart_status
from ..services.autostart import set_preference_and_apply
from ..services.ai_provider import ai_provider
from ..services.model_discovery import ModelDiscoveryError, discover_models
from ..services.qq_bot import qq_bot_service
from ..services.qq_config import load_qq_config, save_qq_config
from ..services.wecom_bot import wecom_bot_service
from ..services.wecom_config import load_wecom_config, save_wecom_config
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
        text = ai_provider._chat("请回复“连接测试成功”，不要输出其他内容。", config).text
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


@router.get("/qq", response_model=QQSettingsRead)
def read_qq_settings(db: Session = Depends(get_db)):
    config = load_qq_config(db)
    return QQSettingsRead(
        enabled=config.enabled,
        app_id=config.app_id,
        app_secret_configured=config.app_secret_configured,
        sandbox=config.sandbox,
        owner_openid=config.owner_openid,
        allowlist=config.allowlist or [],
        running=qq_bot_service.is_running(),
    )


@router.put("/qq", response_model=QQSettingsRead)
async def update_qq_settings(payload: QQSettingsUpdate, db: Session = Depends(get_db)):
    config = save_qq_config(
        db,
        enabled=payload.enabled,
        app_id=payload.app_id,
        app_secret=payload.app_secret,
        sandbox=payload.sandbox,
        owner_openid=payload.owner_openid,
        allowlist=payload.allowlist,
    )
    await qq_bot_service.apply_saved_config()
    return QQSettingsRead(
        enabled=config.enabled,
        app_id=config.app_id,
        app_secret_configured=config.app_secret_configured,
        sandbox=config.sandbox,
        owner_openid=config.owner_openid,
        allowlist=config.allowlist or [],
        running=qq_bot_service.is_running(),
    )


@router.get("/wecom", response_model=WeComSettingsRead)
def read_wecom_settings(db: Session = Depends(get_db)):
    config = load_wecom_config(db)
    return WeComSettingsRead(
        enabled=config.enabled,
        bot_id=config.bot_id,
        secret_configured=config.secret_configured,
        allowlist=config.allowlist or [],
        running=wecom_bot_service.is_running(),
        last_error=wecom_bot_service.get_last_error(),
    )


@router.put("/wecom", response_model=WeComSettingsRead)
async def update_wecom_settings(payload: WeComSettingsUpdate, db: Session = Depends(get_db)):
    config = save_wecom_config(
        db,
        enabled=payload.enabled,
        bot_id=payload.bot_id,
        secret=payload.secret,
        allowlist=payload.allowlist,
    )
    wecom_bot_service.apply_saved_config()
    return WeComSettingsRead(
        enabled=config.enabled,
        bot_id=config.bot_id,
        secret_configured=config.secret_configured,
        allowlist=config.allowlist or [],
        running=wecom_bot_service.is_running(),
        last_error=wecom_bot_service.get_last_error(),
    )


@router.get("/cost-stats", response_model=CostStatsResponse)
def get_cost_stats(db: Session = Depends(get_db)):
    total = db.query(func.coalesce(func.sum(ReplyHistory.cost_cny), 0.0)).scalar() or 0.0
    budget_row = db.query(Setting).filter(Setting.key == "monthly_budget_cny").first()
    budget = float(budget_row.value) if budget_row and budget_row.value else None
    remaining = round(budget - total, 4) if budget is not None else None
    return CostStatsResponse(
        total_spent_cny=round(total, 4),
        monthly_budget_cny=budget,
        remaining_cny=remaining,
    )


@router.put("/budget")
def update_budget(payload: BudgetRequest, db: Session = Depends(get_db)):
    row = db.query(Setting).filter(Setting.key == "monthly_budget_cny").first()
    if payload.monthly_budget_cny is None:
        if row:
            db.delete(row)
            db.commit()
    else:
        value = str(payload.monthly_budget_cny)
        if row:
            row.value = value
        else:
            db.add(Setting(key="monthly_budget_cny", value=value))
        db.commit()
    return {"monthly_budget_cny": payload.monthly_budget_cny}


@router.get("/autostart", response_model=AutoStartSettingsRead)
def read_autostart_settings(db: Session = Depends(get_db)):
    return get_autostart_status(db).__dict__


@router.put("/autostart", response_model=AutoStartSettingsRead)
def update_autostart_settings(payload: AutoStartSettingsUpdate, db: Session = Depends(get_db)):
    return set_preference_and_apply(db, payload.enabled).__dict__
