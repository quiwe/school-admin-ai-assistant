from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReplyHistory
from ..schemas import DeleteResponse, HistoryCreate, HistoryDeleteRequest, HistoryRead

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


@router.post("/delete", response_model=DeleteResponse)
def delete_history(payload: HistoryDeleteRequest, db: Session = Depends(get_db)):
    ids = sorted(set(payload.ids))
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的历史问题。")
    deleted = db.query(ReplyHistory).filter(ReplyHistory.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return DeleteResponse(ok=True, deleted=deleted)


@router.delete("/{history_id}", response_model=DeleteResponse)
def delete_history_item(history_id: int, db: Session = Depends(get_db)):
    item = db.query(ReplyHistory).filter(ReplyHistory.id == history_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="历史记录不存在。")
    db.delete(item)
    db.commit()
    return DeleteResponse(ok=True, deleted=1)
