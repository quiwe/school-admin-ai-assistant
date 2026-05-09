import math
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models import FAQItem, KnowledgeChunk


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+")
NOISE_WORD_RE = re.compile(
    r"(?:xmlformats\.org|schemaRefs|datastoreItem|WordDocument|MsoDataStore|Microsoft Office Word)",
    re.IGNORECASE,
)


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
    tokens: list[str] = []
    for match in TOKEN_RE.findall(text.lower()):
        if has_cjk(match):
            tokens.extend(cjk_ngrams(match))
        else:
            tokens.append(match)
    return tokens


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def cjk_ngrams(text: str) -> list[str]:
    if len(text) <= 2:
        return [text]

    tokens: list[str] = []
    for size in (2, 3, 4):
        if len(text) < size:
            continue
        tokens.extend(text[index : index + size] for index in range(len(text) - size + 1))
    return tokens


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


def similarity_score(query: str, document: str) -> float:
    bm25_score = bm25_like_score(query, document)
    q_terms = set(tokenize(query))
    d_terms = set(tokenize(document))
    if not q_terms or not d_terms:
        return bm25_score

    overlap = q_terms & d_terms
    overlap_score = len(overlap) / math.sqrt(max(len(q_terms), 1))
    compact_query = compact_text(query)
    compact_document = compact_text(document)
    substring_bonus = 0.0
    if compact_query and compact_query in compact_document:
        substring_bonus = min(1.2, len(compact_query) / 10)
    elif compact_document and len(compact_document) <= 40 and compact_document in compact_query:
        substring_bonus = min(1.0, len(compact_document) / 12)

    return max(bm25_score, overlap_score * 2.4 + substring_bonus)


def compact_text(text: str) -> str:
    return "".join(TOKEN_RE.findall(text.lower()))


def retrieve_references(db: Session, question: str, limit: int = 5) -> list[RetrievedReference]:
    candidates: list[RetrievedReference] = []

    faqs = db.query(FAQItem).filter(FAQItem.allow_auto_reply.is_(True)).all()
    for faq in faqs:
        score = max(
            similarity_score(question, faq.question) * 1.35,
            similarity_score(question, f"{faq.question}\n{faq.answer}"),
        )
        if score > 0.12:
            candidates.append(
                RetrievedReference(
                    title=f"FAQ：{faq.question[:40]}",
                    content=f"问：{faq.question}\n答：{faq.answer}",
                    score=score + 0.35,
                    source_type="faq",
                )
            )

    chunks = db.query(KnowledgeChunk).all()
    for chunk in chunks:
        score = similarity_score(question, chunk.chunk_text)
        if score > 0.12:
            title = chunk.file.filename if chunk.file else "知识库文件"
            candidates.append(
                RetrievedReference(
                    title=title,
                    content=clean_reference_text(chunk.chunk_text),
                    score=score,
                    source_type="knowledge",
                )
            )

    candidates.sort(key=lambda item: item.score, reverse=True)
    if not candidates:
        return []
    cutoff = max(0.12, candidates[0].score * 0.3)
    return [candidate for candidate in candidates if candidate.score >= cutoff][:limit]


def clean_reference_text(text: str) -> str:
    text = NOISE_WORD_RE.sub(" ", text)
    text = "".join(char if is_reference_char(char) else " " for char in text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    useful_lines = [line for line in lines if line and has_enough_readable_text(line)]
    return "\n".join(useful_lines).strip() or text.strip()


def is_reference_char(char: str) -> bool:
    if char in "\r\n\t ":
        return True
    if char.isascii():
        return char.isprintable()
    if "\u4e00" <= char <= "\u9fff":
        return True
    if "\u3000" <= char <= "\u303f":
        return True
    if "\uff00" <= char <= "\uffef":
        return True
    return False


def has_enough_readable_text(line: str) -> bool:
    readable = sum(1 for char in line if char.isalnum() or "\u4e00" <= char <= "\u9fff")
    return readable >= 4 and readable / max(len(line), 1) >= 0.35


def confidence_from_references(references: list[RetrievedReference]) -> float:
    if not references:
        return 0.0
    top = references[0].score
    confidence = min(0.92, 0.42 + top / 3.5 + min(len(references), 5) * 0.04)
    return round(confidence, 2)
