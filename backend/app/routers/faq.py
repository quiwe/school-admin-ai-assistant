from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FAQItem
from ..schemas import FAQCreate, FAQRead, FAQUpdate

router = APIRouter(prefix="/api/faq", tags=["faq"])


@router.post("/create", response_model=FAQRead)
def create_faq(payload: FAQCreate, db: Session = Depends(get_db)):
    item = FAQItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/list", response_model=list[FAQRead])
def list_faq(keyword: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(FAQItem).order_by(FAQItem.updated_at.desc())
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(FAQItem.question.like(like), FAQItem.answer.like(like)))
    if category:
        query = query.filter(FAQItem.category == category)
    return query.all()


@router.put("/{faq_id}", response_model=FAQRead)
def update_faq(faq_id: int, payload: FAQUpdate, db: Session = Depends(get_db)):
    item = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ 不存在。")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{faq_id}")
def delete_faq(faq_id: int, db: Session = Depends(get_db)):
    item = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="FAQ 不存在。")
    db.delete(item)
    db.commit()
    return {"ok": True}
