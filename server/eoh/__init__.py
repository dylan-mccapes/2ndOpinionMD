# server/eoh/__init__.py
"""
EoH (Ethos of Health) Router Module

This module provides LLM-based routing for EoH modules, selecting which modules
to use and where to look in the database/doc corpus based on question type.

Note: eoh_llm_router is loaded lazily so that importing lightweight submodules
(e.g. patient_timeline_vision) does not require openai or other heavy deps.
"""

from .module_index import MODULE_INDEX

__all__ = ["MODULE_INDEX", "eoh_llm_router"]


def __getattr__(name: str):
    if name == "eoh_llm_router":
        from .router_llm import eoh_llm_router

        return eoh_llm_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
