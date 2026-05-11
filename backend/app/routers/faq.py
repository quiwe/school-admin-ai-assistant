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
from ..services.rag import similarity_score

router = APIRouter(prefix="/api/faq", tags=["faq"])

FAQ_EXCEL_EXTENSIONS = {".xls", ".xlsx"}
FAQ_DUPLICATE_THRESHOLD = 2.35


@router.post("/create", response_model=FAQRead)
def create_faq(payload: FAQCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"force"})
    duplicate = find_similar_faq(db, data["question"])
    if duplicate and not payload.force:
        raise HTTPException(
            status_code=409,
            detail=f"发现相似 FAQ：{duplicate.question[:60]}。如确认仍要新增，请使用强制保存。",
        )
    item = FAQItem(**data)
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


@router.get("/similar", response_model=list[FAQRead])
def similar_faq(question: str, exclude_id: int | None = None, db: Session = Depends(get_db)):
    matches = find_similar_faqs(db, question, exclude_id=exclude_id)
    return [item for item, _score in matches[:5]]


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

    imported = 0
    skipped_duplicates = 0
    seen_questions: list[str] = []
    for row in rows:
        question = row["question"]
        if is_duplicate_question(db, question) or any(similarity_score(question, seen) >= FAQ_DUPLICATE_THRESHOLD for seen in seen_questions):
            skipped_duplicates += 1
            continue
        db.add(
            FAQItem(
                question=question,
                answer=row["answer"],
                category=row.get("category") or "其他",
                allow_auto_reply=True,
            )
        )
        seen_questions.append(question)
        imported += 1
    db.commit()
    return FAQImportResponse(imported=imported, skipped_duplicates=skipped_duplicates)


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
    updates = payload.model_dump(exclude_unset=True)
    if "question" in updates and is_duplicate_question(db, updates["question"], exclude_id=faq_id):
        raise HTTPException(status_code=409, detail="发现相似 FAQ，请先合并已有 FAQ 或修改问题表述。")
    for key, value in updates.items():
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


def find_similar_faq(db: Session, question: str, exclude_id: int | None = None) -> FAQItem | None:
    matches = find_similar_faqs(db, question, exclude_id=exclude_id)
    return matches[0][0] if matches else None


def is_duplicate_question(db: Session, question: str, exclude_id: int | None = None) -> bool:
    return find_similar_faq(db, question, exclude_id=exclude_id) is not None


def find_similar_faqs(db: Session, question: str, exclude_id: int | None = None) -> list[tuple[FAQItem, float]]:
    clean_question = question.strip()
    if not clean_question:
        return []
    query = db.query(FAQItem)
    if exclude_id is not None:
        query = query.filter(FAQItem.id != exclude_id)
    matches: list[tuple[FAQItem, float]] = []
    for item in query.all():
        score = max(
            similarity_score(clean_question, item.question),
            similarity_score(clean_question, f"{item.question}\n{item.answer}") * 0.88,
        )
        if score >= FAQ_DUPLICATE_THRESHOLD:
            matches.append((item, score))
    matches.sort(key=lambda pair: pair[1], reverse=True)
    return matches
