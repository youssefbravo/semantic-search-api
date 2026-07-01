import io

from pypdf import PdfReader


def extract_text(data: bytes, content_type: str, filename: str) -> str:
    """Extract plain text from an uploaded document.

    Supports PDF (via pypdf) and plain text / markdown. Unknown types are decoded
    as UTF-8 best-effort so we degrade gracefully rather than 500.
    """
    name = (filename or "").lower()
    is_pdf = content_type == "application/pdf" or name.endswith(".pdf")
    if is_pdf:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    return data.decode("utf-8", errors="replace")
