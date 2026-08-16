from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now_utc() -> datetime:
    """返回 naive UTC 时间，等价于已弃用的 datetime.utcnow()。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="其他", index=True)
    parsed_text: Mapped[str] = mapped_column(Text, default="")
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=_now_utc)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="indexed")

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", cascade="all, delete-orphan", back_populates="file"
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("knowledge_files.id"), index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    file: Mapped[KnowledgeFile] = relationship("KnowledgeFile", back_populates="chunks")


class FAQItem(Base):
    __tablename__ = "faq_items"
    __table_args__ = (
        Index("ix_faq_items_category_auto", "category", "allow_auto_reply"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="其他", index=True)
    allow_auto_reply: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now_utc, onupdate=_now_utc)


class ReplyHistory(Base):
    __tablename__ = "reply_history"
    __table_args__ = (
        Index("ix_reply_history_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_question: Mapped[str] = mapped_column(Text, nullable=False)
    ai_answer: Mapped[str] = mapped_column(Text, nullable=False)
    final_answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="其他", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    need_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_cny: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now_utc)


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, default="")
