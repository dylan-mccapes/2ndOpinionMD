"""
PDF rasterization helpers backed by pypdfium2 (pure-pip, no poppler required).

Rasterizes selected pages of a PDF into PIL RGB images at a requested DPI.
The default DPI (220) is chosen to balance OCR accuracy against inference time
for typical medical-record scans. Bump to 300 for dense forms, drop to 150 for
clean born-digital scans.
"""
from __future__ import annotations

import io
import logging
from typing import Iterable, Iterator, Optional, Tuple

import pypdfium2 as pdfium
from PIL import Image

logger = logging.getLogger(__name__)


def _open_doc(pdf_bytes: bytes, password: Optional[str] = None) -> pdfium.PdfDocument:
    """Open a PdfDocument, decrypting if a password is supplied or needed."""
    if password:
        doc = pdfium.PdfDocument(pdf_bytes, password=password.encode())
    else:
        doc = pdfium.PdfDocument(pdf_bytes)
        # Probe whether the doc is locked without a password.
        # pypdfium2 raises on get_page() if encrypted and no password given.
        # We surface a cleaner error here.
        try:
            _ = len(doc)
        except Exception as e:
            doc.close()
            raise ValueError(
                f"PDF may be encrypted — provide `password` parameter. ({e})"
            )
    return doc


def pdf_page_count(pdf_bytes: bytes, password: Optional[str] = None) -> int:
    """Return total page count of a PDF given as bytes."""
    doc = _open_doc(pdf_bytes, password)
    try:
        return len(doc)
    finally:
        doc.close()


def rasterize_pdf_pages(
    pdf_bytes: bytes,
    *,
    pages: Optional[Iterable[int]] = None,
    dpi: int = 220,
    max_dimension: int = 4000,
    password: Optional[str] = None,
    skip_errors: bool = True,
) -> Iterator[Tuple[int, Image.Image]]:
    """Yield (page_num, PIL.Image) for each requested 1-indexed page.

    If `pages` is None, every page is yielded. Pages are clamped to the
    document's range and silently skipped if out of bounds.

    `password` decrypts password-protected PDFs (most common cause of
    PdfiumError: Failed to load page).

    `skip_errors` (default True) skips individual corrupt/unrenderable pages
    instead of raising, so a single bad page doesn't abort a 4000-page run.

    `max_dimension` caps the long edge of each rasterized page to protect
    VRAM — very large DPI x page-size combinations can otherwise produce
    10000+ pixel images that blow out the OCR model.
    """
    scale = dpi / 72.0
    doc = _open_doc(pdf_bytes, password)
    try:
        n_pages = len(doc)
        if pages is None:
            wanted = list(range(1, n_pages + 1))
        else:
            wanted = [p for p in pages if 1 <= p <= n_pages]

        for page_num in wanted:
            try:
                page = doc[page_num - 1]
            except Exception as e:
                if skip_errors:
                    logger.warning("Skipping page %d — failed to load: %s", page_num, e)
                    continue
                raise

            try:
                pil = page.render(scale=scale).to_pil().convert("RGB")
            except Exception as e:
                if skip_errors:
                    logger.warning("Skipping page %d — render failed: %s", page_num, e)
                    continue
                raise
            finally:
                page.close()

            longest = max(pil.size)
            if longest > max_dimension:
                ratio = max_dimension / longest
                new_size = (int(pil.size[0] * ratio), int(pil.size[1] * ratio))
                pil = pil.resize(new_size, Image.LANCZOS)

            yield page_num, pil
    finally:
        doc.close()


def rasterize_single_page_bytes(
    pdf_bytes: bytes,
    page_num: int,
    *,
    dpi: int = 220,
    fmt: str = "PNG",
    password: Optional[str] = None,
) -> bytes:
    """Render one page and return its bytes (useful for debugging / previews)."""
    for _, img in rasterize_pdf_pages(
        pdf_bytes, pages=[page_num], dpi=dpi, password=password,
    ):
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()
    raise IndexError(f"Page {page_num} not found in PDF")
