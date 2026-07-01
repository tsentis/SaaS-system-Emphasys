"""PDF text extraction with a per-page structure.

Native text is read with pypdf. Scanned/image PDFs (little or no extractable text) are
candidates for OCR — a Tesseract fallback is planned; for now such pages yield empty
strings and the caller can flag low-text documents.
"""

import io
from dataclasses import dataclass


@dataclass
class ExtractedText:
    pages: list[str]

    @property
    def full_text(self) -> str:
        return "\n\n".join(self.pages)

    @property
    def char_count(self) -> int:
        return sum(len(p) for p in self.pages)


def extract_text(data: bytes) -> ExtractedText:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 — a bad page shouldn't abort the whole doc
            pages.append("")
    return ExtractedText(pages=pages)
