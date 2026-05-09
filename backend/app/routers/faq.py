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
from ..schemas import FAQCreate, FAQImportResponse, FAQRead, FAQUpdate
from ..services.file_parser import FileParseError, extract_faq_rows_from_spreadsheet

router = APIRouter(prefix="/api/faq", tags=["faq"])

FAQ_EXCEL_EXTENSIONS = {".xls", ".xlsx"}


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


@router.post("/import", response_model=FAQImportResponse)
async def import_faq(file: UploadFile = File(...), db: Session = Depends(get_db)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in FAQ_EXCEL_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持 XLS 或 XLSX FAQ 文件。")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空。")

    with NamedTemporaryFile(suffix=suffix, delete=False) as temp:
        temp_path = Path(temp.name)
        temp.write(content)

    try:
        rows = extract_faq_rows_from_spreadsheet(temp_path)
    except FileParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"FAQ 文件解析失败：{exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)

    if not rows:
        raise HTTPException(status_code=400, detail="未识别到 FAQ 数据。请确认表头包含“问题”和“答案”，可选“分类”。")

    for row in rows:
        db.add(
            FAQItem(
                question=row["question"],
                answer=row["answer"],
                category=row.get("category") or "其他",
                allow_auto_reply=True,
            )
        )
    db.commit()
    return FAQImportResponse(imported=len(rows))


@router.get("/export")
def export_faq(keyword: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(FAQItem).order_by(FAQItem.updated_at.desc())
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(FAQItem.question.like(like), FAQItem.answer.like(like)))
    if category:
        query = query.filter(FAQItem.category == category)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "FAQ"
    sheet.append(["问题", "答案", "分类"])
    for item in query.all():
        sheet.append([item.question, item.answer, item.category])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="faq-export.xlsx"'}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


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
