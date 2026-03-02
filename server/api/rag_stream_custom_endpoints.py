# server/api/rag_stream_custom_endpoints.py
#
# Thin aggregator — replaces 5,700-line monolith.
#
# Split into four mode modules (one per clinical mode):
#
#   rag_stream_shared.py     — shared infrastructure, router object, QA grader
#   rag_stream_ask.py        — ASK mode + CODING mode generators + routes
#                              + synthesize_valyu_evidence helper
#   rag_stream_eoh.py        — EoH (Ethos-of-Health) mode helpers + generator + route
#   rag_stream_detective.py  — EoHD Detective mode helpers + generators + routes
#
# app_postgres.py imports: `from .rag_stream_custom_endpoints import router as rag_stream_custom_router`
# That import is unchanged — router is still exported from here.
#
# Route registration happens when the mode modules are imported below.
# All @router.post / @router.get decorators in each module attach to the
# shared router object defined in rag_stream_shared.py.

from .rag_stream_shared import router  # noqa: F401  — re-exported for app_postgres.py

# Import mode modules — this triggers @router.post / @router.get registration
from . import rag_stream_ask       # noqa: F401
from . import rag_stream_eoh       # noqa: F401
from . import rag_stream_detective  # noqa: F401

__all__ = ["router"]
