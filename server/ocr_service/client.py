"""
Async HTTP client for calling the 2OPMD OCR Forge service.

The main server's timeline ingestion pipeline uses this client to OCR PDF
pages where `pypdf` extracted empty text (i.e. scanned/image-only pages).

Usage:
    from server.ocr_service.client import OcrForgeClient, OCR_FORGE_DEFAULT_URL

    async with OcrForgeClient(OCR_FORGE_DEFAULT_URL) as client:
        healthy = await client.health()
        if healthy:
            pages_text = await client.ocr_pdf_range(
                pdf_path="data/timeline.pdf",
                pages=[17, 42, 103],
            )

Environment:
    OCR_FORGE_URL   Base URL of the OCR Forge (default: http://localhost:8765).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import httpx

logger = logging.getLogger(__name__)

OCR_FORGE_DEFAULT_URL = os.getenv("OCR_FORGE_URL", "http://localhost:8765")
OCR_FORGE_DEFAULT_TIMEOUT = float(os.getenv("OCR_FORGE_TIMEOUT", "1800"))


class OcrForgeClient:
    def __init__(
        self,
        base_url: str = OCR_FORGE_DEFAULT_URL,
        timeout: float = OCR_FORGE_DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OcrForgeClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("OcrForgeClient used outside `async with` block")
        return self._require_client()

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("OcrForgeClient used outside `async with` block")
        return self._client

    # ---------------------- Health ----------------------

    async def health(self) -> Optional[Dict[str, Any]]:
        """Return parsed /health JSON, or None if the service is unreachable."""
        client = self._require_client()
        try:
            r = await client.get("/health")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning("OCR Forge health check failed: %s", e)
            return None

    # ---------------------- Image ----------------------

    async def ocr_image_bytes(
        self, data: bytes, filename: str = "image.png",
    ) -> Dict[str, Any]:
        client = self._require_client()
        r = await client.post(
            "/ocr/image",
            files={"file": (filename, data, "application/octet-stream")},
        )
        r.raise_for_status()
        return r.json()

    # ---------------------- PDF ----------------------

    async def ocr_pdf(
        self,
        pdf_path: str,
        *,
        dpi: int = 220,
        max_dimension: int = 4000,
        skip_empty: bool = False,
        password: Optional[str] = None,
    ) -> Dict[int, str]:
        """OCR every page of a PDF. Returns {page_num: text}."""
        client = self._require_client()
        p = Path(pdf_path)
        params: Dict[str, str] = {
            "dpi": str(dpi),
            "max_dimension": str(max_dimension),
            "skip_empty": str(skip_empty).lower(),
        }
        if password:
            params["password"] = password
        with p.open("rb") as f:
            r = await client.post(
                "/ocr/pdf",
                files={"file": (p.name, f, "application/pdf")},
                params=params,
            )
        r.raise_for_status()
        payload = r.json()
        return {int(k): v for k, v in (payload.get("pages") or {}).items()}

    async def ocr_pdf_range(
        self,
        pdf_path: str,
        *,
        pages: Optional[Sequence[int]] = None,
        start_page: int = 1,
        end_page: Optional[int] = None,
        dpi: int = 220,
        max_dimension: int = 4000,
        skip_empty: bool = False,
        password: Optional[str] = None,
    ) -> Dict[int, str]:
        """OCR a subset of PDF pages. If `pages` is provided, it takes precedence.

        Returns {page_num: text}.
        """
        client = self._require_client()
        p = Path(pdf_path)
        data_fields: Dict[str, str] = {
            "start_page": str(start_page),
            "dpi": str(dpi),
            "max_dimension": str(max_dimension),
            "skip_empty": str(skip_empty).lower(),
        }
        if end_page is not None:
            data_fields["end_page"] = str(end_page)
        if pages:
            data_fields["pages_csv"] = ",".join(str(x) for x in pages)
        if password:
            data_fields["password"] = password

        with p.open("rb") as f:
            r = await client.post(
                "/ocr/pdf/range",
                files={"file": (p.name, f, "application/pdf")},
                data=data_fields,
            )
        r.raise_for_status()
        payload = r.json()
        return {int(k): v for k, v in (payload.get("pages") or {}).items()}

    async def pdf_page_count(
        self,
        pdf_path: str,
        *,
        password: Optional[str] = None,
    ) -> int:
        client = self._require_client()
        p = Path(pdf_path)
        data_fields: Dict[str, str] = {}
        if password:
            data_fields["password"] = password
        with p.open("rb") as f:
            r = await client.post(
                "/ocr/pdf/page_count",
                files={"file": (p.name, f, "application/pdf")},
                data=data_fields or None,
            )
        r.raise_for_status()
        return int(r.json().get("page_count", 0))


# ---------------------------------------------------------------------------
# Convenience single-shot helpers (for callers that don't want to manage a
# long-lived client).
# ---------------------------------------------------------------------------

async def ocr_pdf_pages_via_forge(
    pdf_path: str,
    pages: Sequence[int],
    *,
    base_url: str = OCR_FORGE_DEFAULT_URL,
    dpi: int = 220,
) -> Dict[int, str]:
    """One-shot: OCR a specific set of pages via the forge."""
    async with OcrForgeClient(base_url) as client:
        return await client.ocr_pdf_range(pdf_path, pages=list(pages), dpi=dpi)


async def forge_is_up(base_url: str = OCR_FORGE_DEFAULT_URL) -> bool:
    async with OcrForgeClient(base_url) as client:
        health = await client.health()
    return bool(health and health.get("status") == "ready")
