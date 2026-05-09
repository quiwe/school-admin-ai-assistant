from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FAQItem
from ..schemas import FAQCreate, FAQRead, FAQUpdate
from ..services.file_parser import extract_faq_rows_from_spreadsheet

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


@router.post("/import")
async def import_faq(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 文件。")

    content = await file.read()
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        rows = extract_faq_rows_from_spreadsheet(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not rows:
        raise HTTPException(status_code=400, detail="未找到有效 FAQ 行，请确保表头包含"问题"和"答案"列。")

    created = 0
    for row in rows:
        db.add(
            FAQItem(
                question=row["question"],
                answer=row["answer"],
                category=row.get("category") or "其他",
                allow_auto_reply=True,
            )
        )
        created += 1

    db.commit()
    return {"ok": True, "imported": created}


@router.get("/export")
def export_faq(db: Session = Depends(get_db)):
    items = db.query(FAQItem).order_by(FAQItem.category, FAQItem.id).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "FAQ"
    ws.append(["问题", "答案", "分类"])
    for item in items:
        ws.append([item.question, item.answer, item.category])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=faq_export.xlsx"},
    )
