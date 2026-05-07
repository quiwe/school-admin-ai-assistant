import math
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models import FAQItem, KnowledgeChunk


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


@dataclass
class RetrievedReference:
    title: str
    content: str
    score: float
    source_type: str


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    clean = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        chunks.append(clean[start:end].strip())
        if end == len(clean):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def bm25_like_score(query: str, document: str) -> float:
    q_terms = tokenize(query)
    d_terms = tokenize(document)
    if not q_terms or not d_terms:
        return 0.0
    doc_len = len(d_terms)
    frequencies: dict[str, int] = {}
    for term in d_terms:
        frequencies[term] = frequencies.get(term, 0) + 1
    score = 0.0
    for term in set(q_terms):
        tf = frequencies.get(term, 0)
        if tf:
            score += (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * doc_len / 120))
    return score / math.sqrt(max(len(set(q_terms)), 1))


def retrieve_references(db: Session, question: str, limit: int = 5) -> list[RetrievedReference]:
    candidates: list[RetrievedReference] = []

    faqs = db.query(FAQItem).filter(FAQItem.allow_auto_reply.is_(True)).all()
    for faq in faqs:
        score = max(
            bm25_like_score(question, faq.question),
            bm25_like_score(question, f"{faq.question}\n{faq.answer}") * 0.9,
        )
        if score > 0:
            candidates.append(
                RetrievedReference(
                    title=f"FAQ：{faq.question[:40]}",
                    content=f"问：{faq.question}\n答：{faq.answer}",
                    score=score + 0.2,
                    source_type="faq",
                )
            )

    chunks = db.query(KnowledgeChunk).all()
    for chunk in chunks:
        score = bm25_like_score(question, chunk.chunk_text)
        if score > 0:
            title = chunk.file.filename if chunk.file else "知识库文件"
            candidates.append(
                RetrievedReference(
                    title=title,
                    content=chunk.chunk_text,
                    score=score,
                    source_type="knowledge",
                )
            )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:limit]


def confidence_from_references(references: list[RetrievedReference]) -> float:
    if not references:
        return 0.0
    top = references[0].score
    confidence = min(0.92, 0.42 + top / 3.5 + min(len(references), 5) * 0.04)
    return round(confidence, 2)
