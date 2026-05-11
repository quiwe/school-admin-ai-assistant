import httpx
from openai import OpenAI
from sqlalchemy.orm import Session

from .runtime_config import (
    PROVIDER_MAP,
    get_provider_api_key,
    get_provider_base_url,
    get_provider_model,
    normalize_provider_id,
)


class ModelDiscoveryError(RuntimeError):
    pass


def discover_models(db: Session, provider_id: str, api_key: str | None = None, base_url: str | None = None) -> list[str]:
    normalized_provider_id = normalize_provider_id(provider_id)
    preset = PROVIDER_MAP[normalized_provider_id]
    resolved_base_url = (base_url or "").strip() or get_provider_base_url(db, preset)
    resolved_api_key = (api_key or "").strip() or get_provider_api_key(db, normalized_provider_id)

    if preset.provider_type == "ollama_native":
        models = discover_ollama_models(resolved_base_url)
    elif preset.provider_type == "anthropic_native":
        models = discover_anthropic_models(resolved_base_url, resolved_api_key)
    elif preset.provider_type == "gemini_native":
        models = discover_gemini_models(resolved_base_url, resolved_api_key)
    else:
        models = discover_openai_compatible_models(resolved_base_url, resolved_api_key)

    if not models:
        models = [get_provider_model(db, preset)]
    return models


def discover_openai_compatible_models(base_url: str, api_key: str | None) -> list[str]:
    try:
        client = OpenAI(api_key=api_key or "not-needed", base_url=base_url)
        response = client.models.list()
        models = [model.id for model in response.data if model.id]
        return sorted(set(models), key=models.index)
    except Exception as exc:
        raise ModelDiscoveryError(f"模型列表获取失败，请检查 API Key、Base URL 或该服务是否支持 /models：{exc}") from exc


def discover_ollama_models(base_url: str) -> list[str]:
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(f"{base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            data = response.json()
        models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
        return sorted(set(models), key=models.index)
    except Exception as exc:
        raise ModelDiscoveryError(f"Ollama 模型列表获取失败，请确认 Ollama 已启动：{exc}") from exc


def discover_anthropic_models(base_url: str, api_key: str | None) -> list[str]:
    if not api_key:
        return ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-haiku-20241022"]
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            )
            response.raise_for_status()
            data = response.json()
        models = [item.get("id", "") for item in data.get("data", []) if item.get("id")]
        return sorted(set(models), key=models.index)
    except Exception:
        return ["claude-sonnet-4-20250514", "claude-opus-4-20250514", "claude-3-5-haiku-20241022"]


def discover_gemini_models(base_url: str, api_key: str | None) -> list[str]:
    if not api_key:
        return ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(f"{base_url.rstrip('/')}/models", params={"key": api_key})
            response.raise_for_status()
            data = response.json()
        models = [
            item.get("name", "").removeprefix("models/")
            for item in data.get("models", [])
            if "generateContent" in item.get("supportedGenerationMethods", [])
        ]
        return sorted(set(model for model in models if model), key=models.index)
    except Exception:
        return ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]
