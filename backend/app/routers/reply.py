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


@router.post("/generate", response_model=GenerateReplyResponse)
def generate_reply(payload: GenerateReplyRequest, db: Session = Depends(get_db)):
    category = classify_question(payload.question)
    sensitive, _ = detect_sensitive(payload.question)
    references = retrieve_references(db, payload.question, limit=5)
    confidence = confidence_from_references(references)
    need_human_review = sensitive or not references or confidence < 0.45

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
        )

    if not references:
        answer = (
            "同学你好，这个问题目前在已有知识库中没有找到明确依据，需要进一步核实后再回复。"
            "请先补充姓名、学号、专业及相关截图或材料，老师确认具体情况后再给你准确答复。"
        )
        return GenerateReplyResponse(
            answer=answer,
            category=category,
            confidence=0.0,
            need_human_review=True,
            references=[],
        )

    refs_for_ai = [{"title": ref.title, "content": ref.content[:800]} for ref in references]
    try:
        answer = ai_provider.generate_reply(payload.question, refs_for_ai, payload.style, get_ai_config(db))
    except Exception:
        answer = fallback_answer(payload.question, references)

    return GenerateReplyResponse(
        answer=answer.strip(),
        category=category,
        confidence=confidence,
        need_human_review=need_human_review,
        references=response_references,
    )


@router.post("/rewrite")
def rewrite_reply(payload: RewriteReplyRequest, db: Session = Depends(get_db)):
    try:
        answer = ai_provider.rewrite_reply(payload.question, payload.answer, payload.style, get_ai_config(db))
    except Exception:
        answer = local_rewrite(payload.answer, payload.style)
    return {"answer": answer.strip()}


def fallback_answer(question: str, references) -> str:
    top = references[0]
    if top.source_type == "faq" and "答：" in top.content:
        return top.content.split("答：", 1)[1].strip()
    return (
        "同学你好，根据目前查询到的材料，建议先按学院或系统通知要求准备并提交相关信息。"
        "如系统状态或材料内容仍无法确认，请将姓名、学号、专业及截图发给负责老师进一步核实。"
        "后续办理结果以系统显示和学院通知为准。"
    )


def local_rewrite(answer: str, style: str) -> str:
    if style == "shorter":
        return answer[:140] + ("..." if len(answer) > 140 else "")
    if style == "formal":
        return answer.replace("你好", "您好")
    if style == "warmer":
        return "同学你好，请先不用着急。" + answer.removeprefix("同学你好，")
    return answer
