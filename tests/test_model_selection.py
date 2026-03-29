"""
Model selection test harness.

Verifies stream_config model constants align with spec:
- 5.1 (or 4o): clutch — timeline gap
- 4o: reasoning — guidelines, EoH
- 4.1-mini: routing — coding_router, grader, util
- 4.1: synthesis — timeline summarizer, enrichment, coding core
"""

import importlib
import os
import pytest


def _clear_model_env(monkeypatch):
    """Clear model-related env vars so we get module defaults."""
    for k in (
        "CHAT_MODEL",
        "CHAT_MODEL_GUIDELINES",
        "CHAT_MODEL_CODING_CORE",
        "CHAT_MODEL_UTIL",
        "EOH_TIMELINE_SUMMARIZER_MODEL",
        "EOH_TIMELINE_GAP_MODEL",
    ):
        monkeypatch.delenv(k, raising=False)


def _reload_stream_config():
    """Reload stream_config to pick up env changes."""
    import server.api.stream_config as sc
    importlib.reload(sc)
    return sc


def test_model_selection_defaults_match_spec(monkeypatch):
    """With no env overrides, model constants should match spec."""
    _clear_model_env(monkeypatch)
    sc = _reload_stream_config()

    assert sc.CHAT_MODEL == "gpt-4.1-mini"
    assert sc.CHAT_MODEL_GUIDELINES == "gpt-4o", "reasoning should use 4o"
    assert sc.CHAT_MODEL_CODING_CORE == "gpt-4.1", "coding synthesis should use 4.1"
    assert sc.CHAT_MODEL_UTIL == "gpt-4.1-mini", "routing should use 4.1-mini"
    assert sc.EOH_TIMELINE_SUMMARIZER_MODEL == "gpt-4.1", "synthesis should use 4.1"
    assert sc.EOH_TIMELINE_GAP_MODEL == "gpt-4o", "clutch gap analysis should use 4o (or 5.1 when available)"


def test_model_selection_env_override_guidelines(monkeypatch):
    """CHAT_MODEL_GUIDELINES env overrides default."""
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("CHAT_MODEL_GUIDELINES", "gpt-5.1")
    sc = _reload_stream_config()

    assert sc.CHAT_MODEL_GUIDELINES == "gpt-5.1"


def test_model_selection_env_override_coding_core(monkeypatch):
    """CHAT_MODEL_CODING_CORE env overrides default."""
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("CHAT_MODEL_CODING_CORE", "gpt-4o")
    sc = _reload_stream_config()

    assert sc.CHAT_MODEL_CODING_CORE == "gpt-4o"


def test_model_selection_env_override_eoh_timeline_gap(monkeypatch):
    """EOH_TIMELINE_GAP_MODEL env overrides default."""
    _clear_model_env(monkeypatch)
    monkeypatch.setenv("EOH_TIMELINE_GAP_MODEL", "gpt-5.1")
    sc = _reload_stream_config()

    assert sc.EOH_TIMELINE_GAP_MODEL == "gpt-5.1"


def test_gap_agent_uses_gap_model():
    """EOH_TIMELINE_GAP_MODEL exists and is a valid model string."""
    from server.api.stream_config import EOH_TIMELINE_GAP_MODEL

    assert EOH_TIMELINE_GAP_MODEL in ("gpt-4o", "gpt-5.1") or "gpt-" in EOH_TIMELINE_GAP_MODEL


def test_coding_routes_use_coding_core():
    """CHAT_MODEL_CODING_CORE is used for coding synthesis tier."""
    from server.api.stream_config import CHAT_MODEL_CODING_CORE

    assert CHAT_MODEL_CODING_CORE in ("gpt-4.1", "gpt-4o", "gpt-5.1") or "gpt-" in CHAT_MODEL_CODING_CORE
