"""Turn an uploaded file into page images Gemma 4 can read.

File type is decided from magic bytes, not the client-supplied name or MIME type.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from PIL import Image, ImageOps

from app.services.gemma import ImageInput

MAX_EDGE_PX = 1600  # keeps requests small while staying legible for small print
JPEG_QUALITY = 85


class UnsupportedFileError(ValueError):
    pass


@dataclass
class PreparedDocument:
    kind: str  # "image" | "pdf"
    mime_type: str
    images: list[ImageInput]
    pdf_text: str | None = None
    total_pages: int = 1
    notes: list[str] = field(default_factory=list)


def sniff_mime(data: bytes) -> str:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise UnsupportedFileError("Unsupported file. Upload a JPG, PNG, WEBP image or a PDF.")


def _normalise_image(raw: bytes) -> ImageInput:
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)  # phone photos are often rotated via EXIF
    except Exception as exc:
        raise UnsupportedFileError("The image could not be opened. Is the file corrupted?") from exc
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return ImageInput(data=buf.getvalue(), mime_type="image/jpeg")


def _prepare_pdf(raw: bytes, max_pages: int) -> PreparedDocument:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise UnsupportedFileError("PDF support requires PyMuPDF (pip install pymupdf).") from exc

    try:
        doc = fitz.open(stream=raw, filetype="pdf")
    except Exception as exc:
        raise UnsupportedFileError("The PDF could not be opened.") from exc
    if doc.needs_pass:
        raise UnsupportedFileError("Password-protected PDFs are not supported.")

    total = doc.page_count
    pages = min(total, max_pages)
    images: list[ImageInput] = []
    texts: list[str] = []
    for i in range(pages):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=150)
        images.append(_normalise_image(pix.tobytes("png")))
        texts.append(page.get_text("text"))
    doc.close()

    notes = []
    if total > pages:
        notes.append(f"Only the first {pages} of {total} pages were analysed.")
    pdf_text = "\n\n".join(t for t in texts if t.strip()) or None
    return PreparedDocument(
        kind="pdf", mime_type="application/pdf", images=images, pdf_text=pdf_text, total_pages=total, notes=notes
    )


def prepare_document(raw: bytes, max_pages: int = 6) -> PreparedDocument:
    if not raw:
        raise UnsupportedFileError("The uploaded file is empty.")
    mime = sniff_mime(raw)
    if mime == "application/pdf":
        return _prepare_pdf(raw, max_pages)
    return PreparedDocument(kind="image", mime_type=mime, images=[_normalise_image(raw)])
