from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models import Setting
from ..settings import settings


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    label: str
    provider_type: str
    default_base_url: str
    default_model: str
    requires_api_key: bool = True
    docs_url: str | None = None
    note: str | None = None


@dataclass
class AIConfig:
    ai_provider: str
    provider_type: str
    api_key: str | None
    model: str
    base_url: str


PROVIDER_PRESETS: list[ProviderPreset] = [
    ProviderPreset(
        id="openai",
        label="OpenAI",
        provider_type="openai_compatible",
        default_base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        docs_url="https://platform.openai.com/docs",
    ),
    ProviderPreset(
        id="deepseek",
        label="DeepSeek",
        provider_type="openai_compatible",
        default_base_url="https://api.deepseek.com",
        default_model="deepseek-v4-flash",
        docs_url="https://api-docs.deepseek.com/",
    ),
    ProviderPreset(
        id="anthropic",
        label="Claude / Anthropic",
        provider_type="anthropic_native",
        default_base_url="https://api.anthropic.com/v1",
        default_model="claude-sonnet-4-20250514",
        docs_url="https://docs.anthropic.com/en/docs/about-claude/models/all-models",
    ),
    ProviderPreset(
        id="gemini",
        label="Google Gemini",
        provider_type="gemini_native",
        default_base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-2.5-flash",
        docs_url="https://ai.google.dev/gemini-api/docs/models",
    ),
    ProviderPreset(
        id="qwen",
        label="通义千问 / 阿里百炼",
        provider_type="openai_compatible",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        docs_url="https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api",
        note="不同地域的 API Key 和 Base URL 可能不同。",
    ),
    ProviderPreset(
        id="zhipu",
        label="智谱 GLM",
        provider_type="openai_compatible",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4.5",
        docs_url="https://docs.bigmodel.cn/",
    ),
    ProviderPreset(
        id="kimi",
        label="Kimi / Moonshot",
        provider_type="openai_compatible",
        default_base_url="https://api.moonshot.ai/v1",
        default_model="kimi-latest",
        docs_url="https://platform.kimi.ai/docs/api/overview",
    ),
    ProviderPreset(
        id="doubao",
        label="豆包 / 火山方舟",
        provider_type="openai_compatible",
        default_base_url="https://ark.cn-beijing.volces.com/api/v3",
        default_model="doubao-seed-1-6-flash",
        docs_url="https://www.volcengine.com/docs/82379",
        note="模型名通常可填写火山方舟推理接入点 ID。",
    ),
    ProviderPreset(
        id="hunyuan",
        label="腾讯混元",
        provider_type="openai_compatible",
        default_base_url="https://api.hunyuan.cloud.tencent.com/v1",
        default_model="hunyuan-turbos-latest",
        docs_url="https://cloud.tencent.com/document/product/1729/97732",
        note="默认使用混元 OpenAI 兼容入口；如账号只开通腾讯云签名接口，可通过自定义兼容网关接入。",
    ),
    ProviderPreset(
        id="siliconflow",
        label="硅基流动 SiliconFlow",
        provider_type="openai_compatible",
        default_base_url="https://api.siliconflow.cn/v1",
        default_model="Qwen/Qwen3-32B",
        docs_url="https://docs.siliconflow.com/",
        note="如使用国际站，可将 Base URL 改为 https://api.siliconflow.com/v1。",
    ),
    ProviderPreset(
        id="minimax",
        label="MiniMax",
        provider_type="openai_compatible",
        default_base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.7",
        docs_url="https://platform.minimax.io/docs/api-reference/text-chat",
    ),
    ProviderPreset(
        id="mistral",
        label="Mistral AI",
        provider_type="openai_compatible",
        default_base_url="https://api.mistral.ai/v1",
        default_model="mistral-large-latest",
        docs_url="https://docs.mistral.ai/api/",
    ),
    ProviderPreset(
        id="cohere",
        label="Cohere",
        provider_type="openai_compatible",
        default_base_url="https://api.cohere.com/compatibility/v1",
        default_model="command-a-03-2025",
        docs_url="https://docs.cohere.com/v2/docs/models",
        note="Cohere 原生 Rerank 很适合知识库重排；当前先使用其 OpenAI 兼容聊天入口。",
    ),
    ProviderPreset(
        id="pangu",
        label="华为云盘古 / ModelArts",
        provider_type="openai_compatible",
        default_base_url="https://infer-modelarts-cn-southwest-2.modelarts-infer.com/api/v2",
        default_model="请输入部署模型名",
        docs_url="https://support.huaweicloud.com/api-pangulm/pangulm_05_0079.html",
        note="华为云不同区域和部署的 Base URL、模型名可能不同，请以控制台 OpenAI 格式调用信息为准。",
    ),
    ProviderPreset(
        id="xiaomi",
        label="小米 MiMo",
        provider_type="openai_compatible",
        default_base_url="https://api.xiaomimimo.com/v1",
        default_model="xiaomi/mimo-v2-flash",
        docs_url="https://mimo.xiaomi.com/",
        note="若控制台提供专属 Token Plan 地址，请用控制台地址覆盖默认 Base URL。",
    ),
    ProviderPreset(
        id="openrouter",
        label="OpenRouter",
        provider_type="openai_compatible",
        default_base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4o-mini",
        docs_url="https://openrouter.ai/docs/quickstart",
    ),
    ProviderPreset(
        id="ollama",
        label="Ollama 本地模型",
        provider_type="ollama_native",
        default_base_url="http://localhost:11434",
        default_model="llama3.1",
        requires_api_key=False,
        docs_url="https://github.com/ollama/ollama/blob/main/docs/api.md",
    ),
    ProviderPreset(
        id="lmstudio",
        label="LM Studio 本地模型",
        provider_type="openai_compatible",
        default_base_url="http://localhost:1234/v1",
        default_model="local-model",
        requires_api_key=False,
        docs_url="https://lmstudio.ai/docs/api",
    ),
    ProviderPreset(
        id="custom",
        label="自定义 OpenAI 兼容接口",
        provider_type="openai_compatible",
        default_base_url="http://localhost:8001/v1",
        default_model="custom-model",
        requires_api_key=False,
        note="适合学校私有网关、One API、New API、LiteLLM 等兼容服务。",
    ),
]

PROVIDER_MAP = {provider.id: provider for provider in PROVIDER_PRESETS}


def normalize_provider_id(provider_id: str | None) -> str:
    if provider_id == "local":
        return "ollama"
    if provider_id in PROVIDER_MAP:
        return provider_id
    return "openai"


def provider_setting_key(provider_id: str, field: str) -> str:
    return f"provider_{provider_id}_{field}"


def get_setting(db: Session, key: str) -> str | None:
    record = db.query(Setting).filter(Setting.key == key).first()
    if not record:
        return None
    return record.value


def upsert_setting(db: Session, key: str, value: str) -> None:
    record = db.query(Setting).filter(Setting.key == key).first()
    if record:
        record.value = value
        return
    db.add(Setting(key=key, value=value))


def get_provider_api_key(db: Session, provider_id: str) -> str | None:
    key = get_setting(db, provider_setting_key(provider_id, "api_key"))
    if key:
        return key
    if provider_id == "openai":
        return get_setting(db, "openai_api_key") or settings.openai_api_key
    return None


def get_provider_base_url(db: Session, preset: ProviderPreset) -> str:
    base_url = get_setting(db, provider_setting_key(preset.id, "base_url"))
    if base_url:
        return base_url
    if preset.id == "openai":
        return get_setting(db, "openai_base_url") or settings.openai_base_url or preset.default_base_url
    if preset.id == "ollama":
        return get_setting(db, "local_model_base_url") or settings.local_model_base_url
    return preset.default_base_url


def get_provider_model(db: Session, preset: ProviderPreset) -> str:
    model = get_setting(db, provider_setting_key(preset.id, "model"))
    if model:
        return model
    if preset.id == "openai":
        return get_setting(db, "openai_model") or settings.openai_model
    if preset.id == "ollama":
        return get_setting(db, "local_model_name") or settings.local_model_name
    return preset.default_model


def get_ai_config(db: Session) -> AIConfig:
    provider_id = normalize_provider_id(get_setting(db, "ai_provider") or settings.ai_provider)
    preset = PROVIDER_MAP[provider_id]
    return AIConfig(
        ai_provider=provider_id,
        provider_type=preset.provider_type,
        api_key=get_provider_api_key(db, provider_id),
        model=get_provider_model(db, preset),
        base_url=get_provider_base_url(db, preset),
    )


def list_provider_configs(db: Session) -> list[dict]:
    configs: list[dict] = []
    for preset in PROVIDER_PRESETS:
        configs.append(
            {
                "id": preset.id,
                "label": preset.label,
                "provider_type": preset.provider_type,
                "base_url": get_provider_base_url(db, preset),
                "model": get_provider_model(db, preset),
                "api_key_configured": bool(get_provider_api_key(db, preset.id)),
                "requires_api_key": preset.requires_api_key,
                "docs_url": preset.docs_url,
                "note": preset.note,
            }
        )
    return configs


def save_ai_config(db: Session, payload) -> AIConfig:
    provider = normalize_provider_id(payload.ai_provider)
    upsert_setting(db, "ai_provider", provider)

    for provider_config in payload.providers:
        provider_id = normalize_provider_id(provider_config.id)
        preset = PROVIDER_MAP[provider_id]
        if provider_config.base_url is not None:
            upsert_setting(
                db,
                provider_setting_key(provider_id, "base_url"),
                provider_config.base_url.strip() or preset.default_base_url,
            )
        if provider_config.model is not None:
            upsert_setting(
                db,
                provider_setting_key(provider_id, "model"),
                provider_config.model.strip() or preset.default_model,
            )
        if provider_config.api_key and provider_config.api_key.strip():
            upsert_setting(db, provider_setting_key(provider_id, "api_key"), provider_config.api_key.strip())

    db.commit()
    return get_ai_config(db)
