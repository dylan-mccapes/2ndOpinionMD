"""Runtime config helpers for mock UX development."""
from __future__ import annotations

import os
from pathlib import Path


def mock_user_type() -> str:
    raw = (os.getenv("MOCK_USER_TYPE") or "patient").strip().lower()
    return "doctor" if raw == "doctor" else "patient"


def mock_chat_use_llm() -> bool:
    raw = (os.getenv("MOCK_CHAT_USE_LLM") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def mock_ollama_url() -> str:
    return (os.getenv("MOCK_OLLAMA_URL") or os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434").strip()


def mock_ollama_model() -> str:
    return (os.getenv("MOCK_OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL") or "eoh-llama-lucifer").strip()


def mock_graph_ptv_json() -> Path:
    """
    Source graph for mock graph traversal demos.
    Set MOCK_GRAPH_PTV_JSON to point at your NormanEricRoberts_decrypted-derived PTV file.
    """
    override = (os.getenv("MOCK_GRAPH_PTV_JSON") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "artifacts" / "timeline_ollama_20260329_1805" / "patient_timeline_vision_norman_eric_roberts_20260329_195915.json"
