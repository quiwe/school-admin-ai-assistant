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


def format_references(references: list[dict]) -> str:
    if not references:
        return "无明确依据。"
    return "\n\n".join(
        f"[{index}] {ref['title']}\n{ref['content']}" for index, ref in enumerate(references, start=1)
    )


ai_provider = AIProvider()
