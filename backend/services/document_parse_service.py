from pathlib import Path

from pypdf import PdfReader

from core.errors import bad_request


def parse_document(path: Path, file_type: str) -> str:
    if file_type == "txt":
        text = path.read_text(encoding="utf-8")
    elif file_type == "pdf":
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise bad_request("Unsupported document type")
    text = text.strip()
    if not text:
        raise ValueError("Document contains no extractable text")
    return text


def split_text(text: str, size: int, overlap: int) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Invalid chunk settings")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunk = text[start:start + size].strip()
        if chunk:
            chunks.append(chunk)
        if start + size >= len(text):
            break
        start += size - overlap
    return chunks
