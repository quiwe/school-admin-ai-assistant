from datetime import datetime
from io import BytesIO
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FAQItem, KnowledgeChunk, KnowledgeFile, ReplyHistory, Setting
from ..schemas import BackupImportResponse
from ..services.rag import chunk_text
from .faq import is_duplicate_question

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/export")
def export_data(db: Session = Depends(get_db)):
    payload = {
        "format": "school-admin-ai-assistant-backup",
        "version": 1,
        "exported_at": datetime.utcnow().isoformat(),
        "faq_items": [
            {
                "question": item.question,
                "answer": item.answer,
                "category": item.category,
                "allow_auto_reply": item.allow_auto_reply,
            }
            for item in db.query(FAQItem).order_by(FAQItem.id.asc()).all()
        ],
        "knowledge_files": [
            {
                "filename": item.filename,
                "category": item.category,
                "parsed_text": item.parsed_text,
            }
            for item in db.query(KnowledgeFile).order_by(KnowledgeFile.id.asc()).all()
        ],
        "reply_history": [
            {
                "student_question": item.student_question,
                "ai_answer": item.ai_answer,
                "final_answer": item.final_answer,
                "category": item.category,
                "confidence": item.confidence,
                "need_human_review": item.need_human_review,
            }
            for item in db.query(ReplyHistory).order_by(ReplyHistory.id.asc()).all()
        ],
        "settings": [
            {"key": item.key, "value": item.value}
            for item in db.query(Setting).order_by(Setting.key.asc()).all()
            if not item.key.endswith("_api_key") and item.key not in {"openai_api_key"}
        ],
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"school-admin-ai-assistant-backup-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=BackupImportResponse)
async def import_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="备份文件为空。")
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"备份文件不是有效 JSON：{exc}") from exc
    if payload.get("format") != "school-admin-ai-assistant-backup":
        raise HTTPException(status_code=400, detail="备份文件格式不匹配。")

    imported_faq = 0
    skipped_faq_duplicates = 0
    for row in payload.get("faq_items") or []:
        question = str(row.get("question") or "").strip()
        answer = str(row.get("answer") or "").strip()
        if not question or not answer:
            continue
        if is_duplicate_question(db, question):
            skipped_faq_duplicates += 1
            continue
        db.add(
            FAQItem(
                question=question,
                answer=answer,
                category=str(row.get("category") or "其他").strip() or "其他",
                allow_auto_reply=bool(row.get("allow_auto_reply", True)),
            )
        )
        imported_faq += 1

    imported_knowledge_files = 0
    for row in payload.get("knowledge_files") or []:
        filename = str(row.get("filename") or "").strip()
        parsed_text = str(row.get("parsed_text") or "").strip()
        if not filename or not parsed_text:
            continue
        record = KnowledgeFile(
            filename=filename,
            category=str(row.get("category") or "其他").strip() or "其他",
            parsed_text=parsed_text,
            chunk_count=0,
            status="empty",
        )
        db.add(record)
        db.flush()
        chunks = chunk_text(parsed_text)
        for index, chunk in enumerate(chunks):
            db.add(KnowledgeChunk(file_id=record.id, chunk_text=chunk, chunk_index=index, embedding_id=None))
        record.chunk_count = len(chunks)
        record.status = "indexed" if chunks else "empty"
        imported_knowledge_files += 1

    imported_history = 0
    for row in payload.get("reply_history") or []:
        question = str(row.get("student_question") or "").strip()
        ai_answer = str(row.get("ai_answer") or "").strip()
        final_answer = str(row.get("final_answer") or ai_answer).strip()
        if not question or not final_answer:
            continue
        db.add(
            ReplyHistory(
                student_question=question,
                ai_answer=ai_answer or final_answer,
                final_answer=final_answer,
                category=str(row.get("category") or "其他").strip() or "其他",
                confidence=float(row.get("confidence") or 0.0),
                need_human_review=bool(row.get("need_human_review", False)),
            )
        )
        imported_history += 1

    for row in payload.get("settings") or []:
        key = str(row.get("key") or "").strip()
        value = str(row.get("value") or "")
        if not key or key.endswith("_api_key") or key == "openai_api_key":
            continue
        record = db.query(Setting).filter(Setting.key == key).first()
        if record:
            record.value = value
        else:
            db.add(Setting(key=key, value=value))

    db.commit()
    return BackupImportResponse(
        ok=True,
        imported_faq=imported_faq,
        skipped_faq_duplicates=skipped_faq_duplicates,
        imported_knowledge_files=imported_knowledge_files,
        imported_history=imported_history,
    )
