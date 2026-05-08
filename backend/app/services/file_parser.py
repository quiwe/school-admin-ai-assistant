from pathlib import Path
import re

import olefile
import xlrd
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation
from pypdf import PdfReader


class FileParseError(ValueError):
    pass


SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".xls", ".xlsx"}


def parse_file(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return parse_pdf(path)
        if suffix == ".doc":
            return parse_legacy_office(path, "DOC")
        if suffix == ".docx":
            return parse_docx(path)
        if suffix == ".ppt":
            return parse_legacy_office(path, "PPT")
        if suffix == ".pptx":
            return parse_pptx(path)
        if suffix == ".xls":
            return parse_xls(path)
        if suffix == ".xlsx":
            return parse_xlsx(path)
        if suffix == ".txt":
            return path.read_text(encoding="utf-8-sig")
    except FileParseError:
        raise
    except Exception as exc:
        raise FileParseError(f"文件解析失败：{exc}") from exc
    raise FileParseError("暂不支持该文件类型，请上传 PDF、DOC、DOCX、PPT、PPTX、TXT、XLS 或 XLSX 文件。")


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


def parse_pptx(path: Path) -> str:
    presentation = Presentation(str(path))
    lines: list[str] = []
    for slide_index, slide in enumerate(presentation.slides, start=1):
        slide_lines: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text_frame:
                text = "\n".join(
                    paragraph.text.strip()
                    for paragraph in shape.text_frame.paragraphs
                    if paragraph.text.strip()
                )
                if text:
                    slide_lines.append(text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        slide_lines.append(" | ".join(cells))
        if slide_lines:
            lines.append(f"第{slide_index}页")
            lines.extend(slide_lines)
    return "\n".join(lines).strip()


def parse_xls(path: Path) -> str:
    workbook = xlrd.open_workbook(str(path))
    lines: list[str] = []
    for sheet in workbook.sheets():
        lines.append(f"工作表：{sheet.name}")
        for row_index in range(sheet.nrows):
            values = [
                format_xls_cell(workbook, sheet.cell(row_index, col_index))
                for col_index in range(sheet.ncols)
            ]
            values = [value for value in values if value]
            if values:
                lines.append(" | ".join(values))
    return "\n".join(lines).strip()


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


def parse_legacy_office(path: Path, label: str) -> str:
    if not olefile.isOleFile(str(path)):
        raise FileParseError(f"{label} 文件不是有效的旧版 Office OLE 文件。")

    chunks: list[str] = []
    with olefile.OleFileIO(str(path)) as ole:
        for entry in ole.listdir(streams=True, storages=False):
            stream_name = "/".join(entry)
            try:
                with ole.openstream(entry) as stream:
                    data = stream.read()
            except Exception:
                continue
            text = extract_readable_text(data)
            if text:
                chunks.append(f"{stream_name}\n{text}")

    result = "\n\n".join(chunks).strip()
    if not result:
        raise FileParseError(
            f"旧版 {label} 文件未提取到可读文本。可尝试用 Office/WPS 另存为 DOCX、PPTX、PDF 或 TXT 后再上传。"
        )
    return result


def extract_readable_text(data: bytes) -> str:
    lines: list[str] = []
    for encoding in ("utf-16le", "gb18030", "utf-8"):
        try:
            decoded = data.decode(encoding, errors="ignore")
        except Exception:
            continue
        lines.extend(readable_lines(decoded))

    deduped: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line not in seen:
            seen.add(line)
            deduped.append(line)
    return "\n".join(deduped[:800]).strip()


def readable_lines(text: str) -> list[str]:
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", "\n", text)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    lines: list[str] = []
    for line in normalized.splitlines():
        clean = line.strip()
        if is_readable_line(clean):
            lines.append(clean)
    return lines


def is_readable_line(value: str) -> bool:
    if len(value) < 2:
        return False
    useful = sum(1 for char in value if char.isalnum() or "\u4e00" <= char <= "\u9fff")
    if useful < 2:
        return False
    return useful / max(len(value), 1) >= 0.25


def format_xls_cell(workbook, cell) -> str:
    if cell.ctype == xlrd.XL_CELL_EMPTY:
        return ""
    if cell.ctype == xlrd.XL_CELL_DATE:
        try:
            return str(xlrd.xldate.xldate_as_datetime(cell.value, workbook.datemode)).strip()
        except Exception:
            return str(cell.value).strip()
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        number = cell.value
        if float(number).is_integer():
            return str(int(number))
        return str(number).strip()
    return str(cell.value).strip()


def extract_faq_rows_from_spreadsheet(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".xls":
        return extract_faq_rows_from_xls(path)
    return extract_faq_rows_from_xlsx(path)


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


def extract_faq_rows_from_xls(path: Path) -> list[dict[str, str]]:
    workbook = xlrd.open_workbook(str(path))
    rows: list[dict[str, str]] = []
    for sheet in workbook.sheets():
        if sheet.nrows == 0:
            continue
        headers = [format_xls_cell(workbook, sheet.cell(0, index)) for index in range(sheet.ncols)]
        question_index = find_header(headers, ["问题", "question"])
        answer_index = find_header(headers, ["答案", "answer"])
        category_index = find_header(headers, ["分类", "category"])
        if question_index is None or answer_index is None:
            continue
        for row_index in range(1, sheet.nrows):
            raw_row = tuple(
                format_xls_cell(workbook, sheet.cell(row_index, col_index)) for col_index in range(sheet.ncols)
            )
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
