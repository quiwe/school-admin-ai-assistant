from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReplyHistory
from ..schemas import HistoryCreate, HistoryRead

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/list", response_model=list[HistoryRead])
def list_history(keyword: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ReplyHistory).order_by(ReplyHistory.created_at.desc())
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                ReplyHistory.student_question.like(like),
                ReplyHistory.ai_answer.like(like),
                ReplyHistory.final_answer.like(like),
            )
        )
    if category:
        query = query.filter(ReplyHistory.category == category)
    return query.limit(200).all()


@router.post("/create", response_model=HistoryRead)
def create_history(payload: HistoryCreate, db: Session = Depends(get_db)):
    item = ReplyHistory(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
