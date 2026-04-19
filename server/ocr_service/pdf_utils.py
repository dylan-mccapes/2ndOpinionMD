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


def pdf_page_count(pdf_bytes: bytes) -> int:
    """Return total page count of a PDF given as bytes."""
    doc = pdfium.PdfDocument(pdf_bytes)
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
) -> Iterator[Tuple[int, Image.Image]]:
    """Yield (page_num, PIL.Image) for each requested 1-indexed page.

    If `pages` is None, every page is yielded. Pages are clamped to the
    document's range and silently skipped if out of bounds.

    `max_dimension` caps the long edge of each rasterized page to protect
    VRAM — very large DPI x page-size combinations can otherwise produce
    10000+ pixel images that blow out the OCR model.
    """
    scale = dpi / 72.0
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        n_pages = len(doc)
        if pages is None:
            wanted = list(range(1, n_pages + 1))
        else:
            wanted = [p for p in pages if 1 <= p <= n_pages]

        for page_num in wanted:
            page = doc[page_num - 1]
            try:
                pil = page.render(scale=scale).to_pil().convert("RGB")
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
) -> bytes:
    """Render one page and return its bytes (useful for debugging / previews)."""
    for _, img in rasterize_pdf_pages(pdf_bytes, pages=[page_num], dpi=dpi):
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()
    raise IndexError(f"Page {page_num} not found in PDF")
