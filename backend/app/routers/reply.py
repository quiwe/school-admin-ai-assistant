import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import GenerateReplyRequest, GenerateReplyResponse, Reference, RewriteReplyRequest
from ..services.ai_provider import ai_provider
from ..services.classifier import classify_question
from ..services.rag import confidence_from_references, retrieve_references
from ..services.runtime_config import get_ai_config
from ..services.safety import HUMAN_REVIEW_TEMPLATE, detect_sensitive

router = APIRouter(prefix="/api/reply", tags=["reply"])

RELIABLE_REFERENCE_CONFIDENCE = 0.45


@router.post("/generate", response_model=GenerateReplyResponse)
def generate_reply(payload: GenerateReplyRequest, db: Session = Depends(get_db)):
    category = classify_question(payload.question)
    sensitive, _ = detect_sensitive(payload.question)
    references = retrieve_references(db, payload.question, limit=5)
    confidence = confidence_from_references(references)
    has_reliable_references = bool(references) and confidence >= RELIABLE_REFERENCE_CONFIDENCE

    response_references = [
        Reference(title=ref.title, content=ref.content[:500]) for ref in references
    ]

    if sensitive:
        return GenerateReplyResponse(
            answer=HUMAN_REVIEW_TEMPLATE,
            category=category,
            confidence=confidence,
            need_human_review=True,
            references=response_references,
            ai_used=False,
        )

    if not has_reliable_references:
        answer = (
            "同学你好，这个问题目前在已有知识库中没有找到明确依据，需要进一步核实后再回复。"
            "请先补充姓名、学号、专业及相关截图或材料，老师确认具体情况后再给你准确答复。"
        )
        return GenerateReplyResponse(
            answer=answer,
            category=category,
            confidence=confidence,
            need_human_review=True,
            references=response_references,
            ai_used=False,
        )

    ai_config = get_ai_config(db)
    refs_for_ai = [{"title": ref.title, "content": ref.content[:800]} for ref in references]
    try:
        answer = ai_provider.generate_reply(payload.question, refs_for_ai, payload.style, ai_config)
        if not answer.strip():
            raise RuntimeError("大模型返回了空内容。")
    except Exception as exc:
        return GenerateReplyResponse(
            answer=(
                "已检索到知识库依据，但当前大模型调用失败，暂时不能生成可发送回复。"
                "请到系统设置检查 API Key、Base URL 和模型名称，确认模型连接正常后再生成。"
            ),
            category=category,
            confidence=confidence,
            need_human_review=True,
            references=response_references,
            ai_used=False,
            ai_provider=ai_config.ai_provider,
            ai_model=ai_config.model,
            ai_error=safe_error_message(exc),
        )

    return GenerateReplyResponse(
        answer=answer.strip(),
        category=category,
        confidence=confidence,
        need_human_review=False,
        references=response_references,
        ai_used=True,
        ai_provider=ai_config.ai_provider,
        ai_model=ai_config.model,
    )


@router.post("/rewrite")
def rewrite_reply(payload: RewriteReplyRequest, db: Session = Depends(get_db)):
    try:
        answer = ai_provider.rewrite_reply(payload.question, payload.answer, payload.style, get_ai_config(db))
    except Exception:
        answer = local_rewrite(payload.answer, payload.style)
    return {"answer": answer.strip()}


def safe_error_message(exc: Exception) -> str:
    message = str(exc)
    message = re.sub(r"sk-[A-Za-z0-9_-]{6,}", "sk-***", message)
    message = re.sub(r"([A-Za-z0-9_-]{4})[A-Za-z0-9_-]{12,}", r"\1***", message)
    return message[:500]


def local_rewrite(answer: str, style: str) -> str:
    if style == "shorter":
        return answer[:140] + ("..." if len(answer) > 140 else "")
    if style == "formal":
        return answer.replace("你好", "您好")
    if style == "warmer":
        return "同学你好，请先不用着急。" + answer.removeprefix("同学你好，")
    return answer
