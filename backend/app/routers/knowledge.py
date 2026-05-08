from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FAQItem, KnowledgeChunk, KnowledgeFile
from ..schemas import KnowledgeFileRead, KnowledgeFileUpdate
from ..services.file_parser import (
    FileParseError,
    SUPPORTED_EXTENSIONS,
    extract_faq_rows_from_spreadsheet,
    parse_file,
)
from ..services.rag import chunk_text
from ..settings import settings

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/upload", response_model=KnowledgeFileRead)
async def upload_knowledge(
    file: UploadFile = File(...),
    category: str = Form("其他"),
    import_faq: bool = Form(False),
    db: Session = Depends(get_db),
):
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持 PDF、DOC、DOCX、PPT、PPTX、TXT、XLS、XLSX 文件。")

    stored_name = f"{uuid4().hex}{suffix}"
    stored_path = upload_dir / stored_name
    content = await file.read()
    stored_path.write_bytes(content)

    try:
        parsed_text = parse_file(stored_path)
    except FileParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chunks = chunk_text(parsed_text)
    record = KnowledgeFile(
        filename=file.filename or stored_name,
        category=category,
        parsed_text=parsed_text,
        chunk_count=len(chunks),
        status="indexed" if chunks else "empty",
    )
    db.add(record)
    db.flush()
    for index, chunk in enumerate(chunks):
        db.add(KnowledgeChunk(file_id=record.id, chunk_text=chunk, chunk_index=index, embedding_id=None))

    if import_faq and suffix in {".xlsx", ".xls"}:
        for row in extract_faq_rows_from_spreadsheet(stored_path):
            db.add(
                FAQItem(
                    question=row["question"],
                    answer=row["answer"],
                    category=row.get("category") or category,
                    allow_auto_reply=True,
                )
            )

    db.commit()
    db.refresh(record)
    return record


@router.get("/list", response_model=list[KnowledgeFileRead])
def list_knowledge(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(KnowledgeFile).order_by(KnowledgeFile.upload_time.desc())
    if category:
        query = query.filter(KnowledgeFile.category == category)
    return query.all()


@router.delete("/{file_id}")
def delete_knowledge(file_id: int, db: Session = Depends(get_db)):
    record = db.query(KnowledgeFile).filter(KnowledgeFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="知识库文件不存在。")
    db.delete(record)
    db.commit()
    return {"ok": True}


@router.patch("/{file_id}", response_model=KnowledgeFileRead)
def update_knowledge(file_id: int, payload: KnowledgeFileUpdate, db: Session = Depends(get_db)):
    record = db.query(KnowledgeFile).filter(KnowledgeFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="知识库文件不存在。")
    if payload.category is not None:
        category = payload.category.strip()
        if not category:
            raise HTTPException(status_code=400, detail="分类不能为空。")
        record.category = category
    db.commit()
    db.refresh(record)
    return record


@router.post("/{file_id}/reindex", response_model=KnowledgeFileRead)
def reindex_knowledge(file_id: int, db: Session = Depends(get_db)):
    record = db.query(KnowledgeFile).filter(KnowledgeFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="知识库文件不存在。")
    db.query(KnowledgeChunk).filter(KnowledgeChunk.file_id == file_id).delete()
    chunks = chunk_text(record.parsed_text)
    for index, chunk in enumerate(chunks):
        db.add(KnowledgeChunk(file_id=record.id, chunk_text=chunk, chunk_index=index, embedding_id=None))
    record.chunk_count = len(chunks)
    record.status = "indexed" if chunks else "empty"
    db.commit()
    db.refresh(record)
    return record
