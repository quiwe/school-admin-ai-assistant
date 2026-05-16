from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReplyHistory
from ..schemas import GenerateReplyRequest, StudentGenerateReplyRequest, StudentGenerateReplyResponse
from ..settings import settings
from .reply import generate_reply

router = APIRouter(prefix="/api/student", tags=["student"])


def require_student_access(x_student_access_key: str | None = Header(default=None)) -> None:
    if settings.student_access_key and x_student_access_key == settings.student_access_key:
        return
    raise HTTPException(status_code=403, detail="网页端访问码无效，请使用老师提供的完整网页端地址。")


@router.post("/reply/generate", response_model=StudentGenerateReplyResponse)
def generate_student_reply(
    payload: StudentGenerateReplyRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_student_access),
):
    result = generate_reply(GenerateReplyRequest(question=payload.question, style=payload.style), db)
    history = ReplyHistory(
        student_question=payload.question,
        ai_answer=result.answer,
        final_answer=result.answer,
        category=result.category,
        confidence=result.confidence,
        need_human_review=result.need_human_review,
    )
    db.add(history)
    db.commit()
    return StudentGenerateReplyResponse(
        answer=result.answer,
        category=result.category,
        need_human_review=result.need_human_review,
    )
