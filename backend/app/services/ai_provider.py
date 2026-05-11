from pathlib import Path

import httpx
from openai import OpenAI

from ..services.runtime_config import AIConfig
from ..settings import settings


SYSTEM_PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "system_prompt.txt").read_text(encoding="utf-8")


class AIProvider:
    def generate_reply(self, question: str, references: list[dict], style: str = "normal", config: AIConfig | None = None) -> str:
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

    def rewrite_reply(self, question: str, answer: str, style: str, config: AIConfig | None = None) -> str:
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

    def _chat(self, user_prompt: str, config: AIConfig | None = None) -> str:
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

    def _chat_openai_compatible(self, user_prompt: str, config: AIConfig) -> str:
        client = OpenAI(api_key=config.api_key or "not-needed", base_url=config.base_url)
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def _chat_ollama(self, user_prompt: str, config: AIConfig) -> str:
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
        return data.get("message", {}).get("content", "")

    def _chat_anthropic(self, user_prompt: str, config: AIConfig) -> str:
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
        return "".join(part.get("text", "") for part in parts if part.get("type") == "text").strip()

    def _chat_gemini(self, user_prompt: str, config: AIConfig) -> str:
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
            return ""
        parts = candidates[0].get("content", {}).get("parts") or []
        return "".join(part.get("text", "") for part in parts).strip()


def format_references(references: list[dict]) -> str:
    if not references:
        return "无明确依据。"
    return "\n\n".join(
        f"[{index}] {ref['title']}\n{ref['content']}" for index, ref in enumerate(references, start=1)
    )


ai_provider = AIProvider()
