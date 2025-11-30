# server/eoh/__init__.py
"""
EoH (Ethos of Health) Router Module

This module provides LLM-based routing for EoH modules, selecting which modules
to use and where to look in the database/doc corpus based on question type.
"""

from .module_index import MODULE_INDEX
from .router_llm import eoh_llm_router

__all__ = ["MODULE_INDEX", "eoh_llm_router"]
