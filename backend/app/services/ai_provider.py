from pathlib import Path
from dataclasses import dataclass

import httpx
from openai import OpenAI

from ..services.runtime_config import AIConfig
from ..settings import settings


SYSTEM_PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "system_prompt.txt").read_text(encoding="utf-8")

USD_TO_CNY = 7.2

MODEL_PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": {"cache_hit": 0.0028, "cache_miss": 0.14, "output": 0.28},
    "deepseek-v4-pro": {"cache_hit": 0.003625, "cache_miss": 0.435, "output": 0.87},
    "deepseek-chat": {"cache_hit": 0.0028, "cache_miss": 0.14, "output": 0.28},
    "deepseek-reasoner": {"cache_hit": 0.0028, "cache_miss": 0.14, "output": 0.28},
    "gpt-4o-mini": {"cache_hit": 0.075, "cache_miss": 0.15, "output": 0.6},
    "gpt-4o": {"cache_hit": 1.25, "cache_miss": 2.5, "output": 10.0},
}


@dataclass
class AIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    cache_hit_ratio: float | None = None
    cost_usd: float | None = None
    cost_cny: float | None = None


@dataclass
class AIChatResult:
    text: str
    usage: AIUsage | None = None


class AIProvider:
    def generate_reply(self, question: str, references: list[dict], style: str = "normal", config: AIConfig | None = None) -> AIChatResult:
        context = format_references(references)
        user_prompt = (
            f"学生问题：{question}\n\n"
            f"可用依据：\n{context}\n\n"
            f"回复风格：{style}\n"
            "请先判断可用依据是否能支持回答学生问题。"
            "如果 FAQ 与学生问题只是问法不同但含义一致，可以按 FAQ 标准答案组织回复。"
            "如果依据不能支持回答，请只说明该问题需要进一步核实。"
            "请生成一段可直接复制到微信发送的回复。"
        )
        return self._chat(user_prompt, config)

    def rewrite_reply(self, question: str, answer: str, style: str, config: AIConfig | None = None) -> AIChatResult:
        style_map = {
            "formal": "更正式一点，但不要生硬。",
            "shorter": "更简短一点，保留关键信息。",
            "warmer": "更温和一点，体现理解和安抚。",
        }
        user_prompt = (
            f"学生问题：{question}\n\n当前回复：{answer}\n\n"
            f"改写要求：{style_map.get(style, style)}\n"
            "请只输出改写后的微信回复，不要添加解释。"
        )
        return self._chat(user_prompt, config)

    def _chat(self, user_prompt: str, config: AIConfig | None = None) -> AIChatResult:
        config = config or AIConfig(
            ai_provider=settings.ai_provider,
            provider_type="openai_compatible",
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url or "https://api.openai.com/v1",
        )
        if config.provider_type == "ollama_native":
            return self._chat_ollama(user_prompt, config)
        if config.provider_type == "anthropic_native":
            return self._chat_anthropic(user_prompt, config)
        if config.provider_type == "gemini_native":
            return self._chat_gemini(user_prompt, config)
        return self._chat_openai_compatible(user_prompt, config)

    def _chat_openai_compatible(self, user_prompt: str, config: AIConfig) -> AIChatResult:
        client = OpenAI(api_key=config.api_key or "not-needed", base_url=config.base_url)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return AIChatResult(
            text=response.choices[0].message.content or "",
            usage=usage_from_raw(getattr(response, "usage", None), config.model),
        )

    def _chat_ollama(self, user_prompt: str, config: AIConfig) -> AIChatResult:
        payload = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(f"{config.base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return AIChatResult(
            text=data.get("message", {}).get("content", ""),
            usage=usage_from_raw(data, config.model),
        )

    def _chat_anthropic(self, user_prompt: str, config: AIConfig) -> AIChatResult:
        if not config.api_key:
            raise RuntimeError("Claude / Anthropic 需要 API Key。")
        payload = {
            "model": config.model,
            "max_tokens": 1200,
            "temperature": 0.2,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=90) as client:
            response = client.post(f"{config.base_url.rstrip('/')}/messages", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        parts = data.get("content") or []
        return AIChatResult(
            text="".join(part.get("text", "") for part in parts if part.get("type") == "text").strip(),
            usage=usage_from_raw(data.get("usage"), config.model),
        )

    def _chat_gemini(self, user_prompt: str, config: AIConfig) -> AIChatResult:
        if not config.api_key:
            raise RuntimeError("Google Gemini 需要 API Key。")
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        url = f"{config.base_url.rstrip('/')}/models/{config.model}:generateContent"
        with httpx.Client(timeout=90) as client:
            response = client.post(url, params={"key": config.api_key}, json=payload)
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return AIChatResult(text="", usage=usage_from_raw(data.get("usageMetadata"), config.model))
        parts = candidates[0].get("content", {}).get("parts") or []
        return AIChatResult(
            text="".join(part.get("text", "") for part in parts).strip(),
            usage=usage_from_raw(data.get("usageMetadata"), config.model),
        )


def format_references(references: list[dict]) -> str:
    if not references:
        return "无明确依据。"
    return "\n\n".join(
        f"[{index}] {ref['title']}\n{ref['content']}" for index, ref in enumerate(references, start=1)
    )


def usage_from_raw(raw: object, model: str) -> AIUsage | None:
    data = raw_to_dict(raw)
    if not data:
        return None
    prompt = int_value(data, "prompt_tokens", "prompt_eval_count", "input_tokens", "promptTokenCount")
    completion = int_value(
        data,
        "completion_tokens",
        "eval_count",
        "output_tokens",
        "candidatesTokenCount",
    )
    total = int_value(data, "total_tokens", "totalTokenCount") or prompt + completion
    cache_hit = int_value(
        data,
        "prompt_cache_hit_tokens",
        "cache_read_input_tokens",
        "cachedContentTokenCount",
    )
    explicit_miss = int_value(data, "prompt_cache_miss_tokens")
    cache_miss = explicit_miss if explicit_miss else max(0, prompt - cache_hit)
    if prompt == 0 and completion == 0 and total == 0:
        return None
    denom = cache_hit + cache_miss
    ratio = round(cache_hit / denom, 4) if denom > 0 and cache_hit > 0 else None
    cost_usd = estimate_cost_usd(model, cache_hit, cache_miss, completion)
    return AIUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
        prompt_cache_hit_tokens=cache_hit,
        prompt_cache_miss_tokens=cache_miss,
        cache_hit_ratio=ratio,
        cost_usd=cost_usd,
        cost_cny=round(cost_usd * USD_TO_CNY, 6) if cost_usd is not None else None,
    )


def raw_to_dict(raw: object) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    result: dict[str, object] = {}
    for key in [
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
        "prompt_eval_count",
        "eval_count",
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
    ]:
        if hasattr(raw, key):
            result[key] = getattr(raw, key)
    return result


def int_value(data: dict, *keys: str) -> int:
    for key in keys:
        value = data.get(key)
        if isinstance(value, int | float):
            return int(value)
    return 0


def estimate_cost_usd(model: str, cache_hit: int, cache_miss: int, completion: int) -> float | None:
    pricing = MODEL_PRICING_USD_PER_1M.get(model)
    if not pricing:
        return None
    return round(
        (
            cache_hit * pricing["cache_hit"]
            + cache_miss * pricing["cache_miss"]
            + completion * pricing["output"]
        )
        / 1_000_000,
        6,
    )


ai_provider = AIProvider()
