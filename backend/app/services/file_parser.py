from pathlib import Path

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader


class FileParseError(ValueError):
    pass


def parse_file(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return parse_pdf(path)
        if suffix == ".docx":
            return parse_docx(path)
        if suffix == ".xlsx":
            return parse_xlsx(path)
        if suffix == ".txt":
            return path.read_text(encoding="utf-8-sig")
    except Exception as exc:
        raise FileParseError(f"文件解析失败：{exc}") from exc
    raise FileParseError("暂不支持该文件类型，请上传 PDF、DOCX、TXT 或 XLSX 文件。")


def parse_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"第{index}页\n{text.strip()}")
    return "\n\n".join(pages).strip()


def parse_docx(path: Path) -> str:
    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))
    return "\n".join(paragraphs).strip()


def parse_xlsx(path: Path) -> str:
    workbook = load_workbook(str(path), data_only=True)
    lines: list[str] = []
    for sheet in workbook.worksheets:
        lines.append(f"工作表：{sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            values = [str(value).strip() for value in row if value is not None and str(value).strip()]
            if values:
                lines.append(" | ".join(values))
    return "\n".join(lines).strip()


def extract_faq_rows_from_xlsx(path: Path) -> list[dict[str, str]]:
    workbook = load_workbook(str(path), data_only=True)
    rows: list[dict[str, str]] = []
    for sheet in workbook.worksheets:
        values = list(sheet.iter_rows(values_only=True))
        if not values:
            continue
        headers = [str(cell).strip() if cell is not None else "" for cell in values[0]]
        question_index = find_header(headers, ["问题", "question"])
        answer_index = find_header(headers, ["答案", "answer"])
        category_index = find_header(headers, ["分类", "category"])
        if question_index is None or answer_index is None:
            continue
        for raw_row in values[1:]:
            question = safe_cell(raw_row, question_index)
            answer = safe_cell(raw_row, answer_index)
            if question and answer:
                rows.append(
                    {
                        "question": question,
                        "answer": answer,
                        "category": safe_cell(raw_row, category_index) if category_index is not None else "其他",
                    }
                )
    return rows


def find_header(headers: list[str], candidates: list[str]) -> int | None:
    normalized = [header.lower() for header in headers]
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized.index(candidate.lower())
    return None


def safe_cell(row: tuple, index: int) -> str:
    if index >= len(row) or row[index] is None:
        return ""
    return str(row[index]).strip()
