"""
OCR engine wrapper around EasyOCR.

Loads the reader once on process start, keeps it warm, and exposes simple
methods for OCR'ing PIL images, raw bytes, or numpy arrays.

GPU (CUDA) mode is the default and the whole point of this service. If CUDA
is unavailable we fall back to CPU so /health still works, but the service
should be considered degraded.
"""
from __future__ import annotations

import io
import logging
import threading
import time
from typing import List, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class OcrEngine:
    """Thread-safe wrapper around easyocr.Reader with a GPU-first bias."""

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        gpu: bool = True,
        model_storage_dir: Optional[str] = None,
    ):
        self.languages = languages or ["en"]
        self.requested_gpu = gpu
        self.model_storage_dir = model_storage_dir

        self._reader = None
        self._lock = threading.Lock()

        self.device: str = "cpu"
        self.gpu_available: bool = False
        self._init_error: Optional[str] = None

    # ------------------------------------------------------------------

    def _build_reader(self):
        import easyocr
        import torch

        self.gpu_available = torch.cuda.is_available()
        use_gpu = bool(self.requested_gpu and self.gpu_available)
        self.device = "cuda" if use_gpu else "cpu"

        logger.info(
            "Initializing EasyOCR (languages=%s, gpu=%s, cuda_available=%s)",
            self.languages, use_gpu, self.gpu_available,
        )

        kwargs = dict(lang_list=self.languages, gpu=use_gpu, verbose=False)
        if self.model_storage_dir:
            kwargs["model_storage_directory"] = self.model_storage_dir

        t0 = time.perf_counter()
        self._reader = easyocr.Reader(**kwargs)
        logger.info(
            "EasyOCR ready on %s (%.1fs)", self.device, time.perf_counter() - t0,
        )

    def warmup(self) -> None:
        """Build the reader + run one tiny inference to JIT the CUDA kernels."""
        try:
            with self._lock:
                if self._reader is None:
                    self._build_reader()
            img = Image.new("RGB", (64, 32), color="white")
            self._read_pil(img)
            logger.info("OCR warmup pass complete")
        except Exception as e:
            self._init_error = str(e)
            logger.exception("OCR warmup failed: %s", e)
            raise

    # ------------------------------------------------------------------
    # Reading helpers
    # ------------------------------------------------------------------

    def _read_pil(self, img: Image.Image) -> List[tuple]:
        if self._reader is None:
            with self._lock:
                if self._reader is None:
                    self._build_reader()
        arr = np.array(img.convert("RGB"))
        with self._lock:
            return self._reader.readtext(arr, detail=1, paragraph=False)

    @staticmethod
    def _fragments_to_text(fragments: List[tuple]) -> str:
        """Join OCR fragments into a readable string.

        EasyOCR returns [(bbox, text, conf), ...]. We sort top-to-bottom,
        left-to-right using bbox y-centres, group into lines, and join.
        """
        if not fragments:
            return ""

        rows = []
        for bbox, text, conf in fragments:
            if not text:
                continue
            ys = [p[1] for p in bbox]
            xs = [p[0] for p in bbox]
            y_centre = sum(ys) / len(ys)
            x_left = min(xs)
            rows.append((y_centre, x_left, text, float(conf)))

        rows.sort(key=lambda r: (round(r[0] / 12) * 12, r[1]))

        lines: List[str] = []
        current_line: List[str] = []
        last_y: Optional[float] = None
        line_tol = 14

        for y, _x, text, _conf in rows:
            if last_y is None or abs(y - last_y) <= line_tol:
                current_line.append(text)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [text]
            last_y = y
        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ocr_pil_image(self, img: Image.Image) -> str:
        fragments = self._read_pil(img)
        return self._fragments_to_text(fragments)

    def ocr_image_bytes(self, data: bytes) -> str:
        img = Image.open(io.BytesIO(data))
        return self.ocr_pil_image(img)

    def ocr_ndarray(self, arr: np.ndarray) -> str:
        img = Image.fromarray(arr)
        return self.ocr_pil_image(img)

    def status(self) -> dict:
        return {
            "device": self.device,
            "gpu_available": self.gpu_available,
            "gpu_requested": self.requested_gpu,
            "languages": self.languages,
            "ready": self._reader is not None,
            "init_error": self._init_error,
        }
