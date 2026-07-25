"""Secure extraction of plain text from uploaded job description files."""

import re
from io import BytesIO
from pathlib import Path

from werkzeug.datastructures import FileStorage

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_PREFIXES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/octet-stream",
)


def _sanitize_text(text: str) -> str:
    """Strip control characters and collapse excessive whitespace."""
    text = text.replace("\x00", "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extension(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def validate_upload(file: FileStorage) -> tuple[str | None, tuple[dict, int] | None]:
    if not file or not file.filename:
        return None, ({"error": "No file provided"}, 400)

    ext = _extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        return None, (
            {"error": f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"},
            400,
        )

    content_type = (file.content_type or "").lower()
    if content_type and not any(content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        return None, ({"error": "Unsupported file MIME type"}, 400)

    data = file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return None, ({"error": "File exceeds 5 MB limit"}, 400)

    return ext, None


def extract_text_from_upload(file: FileStorage) -> tuple[str, str, tuple[dict, int] | None]:
    """
    Extract sanitized text from an uploaded file.
    Returns (text, source_type, error_response).
    """
    ext, error = validate_upload(file)
    if error:
        return "", "", error

    file.seek(0)
    data = file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return "", "", ({"error": "File exceeds 5 MB limit"}, 400)

    try:
        if ext == ".txt":
            text = data.decode("utf-8", errors="replace")
            source = "txt"
        elif ext == ".pdf":
            text = _extract_pdf(data)
            source = "pdf"
        elif ext == ".docx":
            text = _extract_docx(data)
            source = "docx"
        else:
            return "", "", ({"error": "Unsupported file type"}, 400)
    except Exception as exc:
        return "", "", ({"error": f"Failed to parse file: {exc}"}, 400)

    sanitized = _sanitize_text(text)
    if len(sanitized) < 40:
        return "", "", ({"error": "Extracted text is too short. Provide a fuller job description."}, 400)

    return sanitized, source, None


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document

    document = Document(BytesIO(data))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)


def sanitize_pasted_text(text: str) -> str:
    return _sanitize_text(text or "")
