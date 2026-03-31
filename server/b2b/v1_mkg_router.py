"""
/v1/mkg/ — B2B versioned router for the Medical Knowledge Graph.

Mounts existing internal ontology/evidence routers behind API-key auth
and per-key rate limiting.  No new logic — just gating + namespacing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from server.b2b.auth import require_scope, B2BContext
from server.b2b.rate_limit import b2b_rate_limit

# --- Import all existing ontology routers ---
from server.api.snomed_routes import router as _snomed
from server.api.hpo_routes import router as _hpo
from server.api.loinc_routes import router as _loinc
from server.api.rxnorm_routes import router as _rxnorm
from server.api.orphanet_routes import router as _orphanet
from server.api.chv_routes import router as _chv
from server.api.clingen_actionability_routes import router as _clingen
from server.api.panelapp_routes import router as _panelapp
from server.api.disgenet_routes import router as _disgenet
from server.api.gwas_routes import router as _gwas
from server.api.neurolex_routes import router as _neurolex
from server.api.guidelines_routes import router as _guidelines
from server.api.diagnostic_rules_routes import router as _diagrules
from server.api.who_routes import router as _who
from server.api.guidelines_va_routes import router as _va
from server.api.guidelines_cdc_routes import router as _cdc
from server.api.rag_routes import router as _rag
from server.api.kg import router as _kg

# ── Build the v1 MKG router ──────────────────────────────────────────────

mkg_router = APIRouter(
    prefix="/v1/mkg",
    tags=["b2b-mkg"],
    dependencies=[
        Depends(require_scope("mkg:read")),
        Depends(b2b_rate_limit),
    ],
)


# ── Proxy helper ──────────────────────────────────────────────────────────
# Each internal router has prefix="/api/snomed" etc.  We re-mount routes
# under /v1/mkg/ by including the router with an overridden prefix that
# replaces "/api/" with "".
#
# Result: /api/snomed/search  →  /v1/mkg/snomed/search
#         /api/hpo/search     →  /v1/mkg/hpo/search
#         /api/rag/ask        →  /v1/mkg/evidence/ask   (special)
#         ...

_ONTOLOGY_ROUTERS = [
    (_snomed,     "/api/snomed",                "/snomed"),
    (_hpo,        "/api/hpo",                   "/hpo"),
    (_loinc,      "/api/loinc",                 "/loinc"),
    (_rxnorm,     "/api/rxnorm",                "/rxnorm"),
    (_orphanet,   "/api/orphanet",              "/orphanet"),
    (_chv,        "/api/chv",                   "/chv"),
    (_clingen,    "/api/clingen/actionability",  "/clingen"),
    (_panelapp,   "/api/panelapp",              "/panelapp"),
    (_disgenet,   "/api/disgenet",              "/disgenet"),
    (_gwas,       "/api/gwas",                  "/gwas"),
    (_neurolex,   "/api/neurolex",              "/neurolex"),
    (_guidelines, "/api/guidelines",            "/guidelines"),
    (_diagrules,  "/api/diagnostic_rules",      "/diagnostic-rules"),
    (_who,        "",                           "/who"),
    (_va,         "/api/guidelines/va",         "/va"),
    (_cdc,        "",                           "/cdc"),
    (_kg,         "/api/kg",                    "/kg"),
]

from fastapi.routing import APIRoute

for _internal_router, _internal_prefix, _b2b_prefix in _ONTOLOGY_ROUTERS:
    for route in _internal_router.routes:
        if not isinstance(route, APIRoute):
            continue
        # Build the new path: strip internal prefix, prepend b2b prefix
        new_path = route.path
        if _internal_prefix and new_path.startswith(_internal_prefix):
            new_path = new_path[len(_internal_prefix):]
        new_path = _b2b_prefix + (new_path or "/")

        mkg_router.add_api_route(
            new_path,
            route.endpoint,
            methods=list(route.methods) if route.methods else ["GET"],
            tags=["b2b-mkg"],
            name=f"b2b_{route.name}" if route.name else None,
        )


# ── Evidence (RAG) — gated behind mkg:evidence scope ─────────────────────

evidence_router = APIRouter(
    prefix="/v1/mkg/evidence",
    tags=["b2b-mkg-evidence"],
    dependencies=[
        Depends(require_scope("mkg:evidence")),
        Depends(b2b_rate_limit),
    ],
)

for route in _rag.routes:
    if not isinstance(route, APIRoute):
        continue
    new_path = route.path
    if new_path.startswith("/api/rag"):
        new_path = new_path[len("/api/rag"):]
    if not new_path:
        new_path = "/"
    evidence_router.add_api_route(
        new_path,
        route.endpoint,
        methods=list(route.methods) if route.methods else ["GET"],
        tags=["b2b-mkg-evidence"],
        name=f"b2b_evidence_{route.name}" if route.name else None,
    )


# ── Health (no auth required) ─────────────────────────────────────────────

health_router = APIRouter(prefix="/v1", tags=["b2b-meta"])


@health_router.get("/health")
async def v1_health():
    return {"status": "ok", "version": "v1"}


@health_router.get("/mkg/sources")
async def v1_sources(ctx: B2BContext = Depends(require_scope("mkg:read"))):
    """List available MKG data sources."""
    return {
        "sources": [
            {"id": "snomed", "name": "SNOMED CT", "prefix": "/v1/mkg/snomed"},
            {"id": "hpo", "name": "Human Phenotype Ontology", "prefix": "/v1/mkg/hpo"},
            {"id": "loinc", "name": "LOINC", "prefix": "/v1/mkg/loinc"},
            {"id": "rxnorm", "name": "RxNorm", "prefix": "/v1/mkg/rxnorm"},
            {"id": "orphanet", "name": "Orphanet", "prefix": "/v1/mkg/orphanet"},
            {"id": "chv", "name": "Consumer Health Vocabulary", "prefix": "/v1/mkg/chv"},
            {"id": "clingen", "name": "ClinGen Actionability", "prefix": "/v1/mkg/clingen"},
            {"id": "panelapp", "name": "PanelApp", "prefix": "/v1/mkg/panelapp"},
            {"id": "disgenet", "name": "DisGeNET", "prefix": "/v1/mkg/disgenet"},
            {"id": "gwas", "name": "GWAS Catalog", "prefix": "/v1/mkg/gwas"},
            {"id": "neurolex", "name": "NeuroLex", "prefix": "/v1/mkg/neurolex"},
            {"id": "guidelines", "name": "Clinical Guidelines", "prefix": "/v1/mkg/guidelines"},
            {"id": "diagnostic-rules", "name": "Diagnostic Rules", "prefix": "/v1/mkg/diagnostic-rules"},
            {"id": "who", "name": "WHO", "prefix": "/v1/mkg/who"},
            {"id": "va", "name": "VA Guidelines", "prefix": "/v1/mkg/va"},
            {"id": "cdc", "name": "CDC Guidelines", "prefix": "/v1/mkg/cdc"},
            {"id": "kg", "name": "Knowledge Graph", "prefix": "/v1/mkg/kg"},
            {"id": "evidence", "name": "RAG Evidence Search", "prefix": "/v1/mkg/evidence"},
        ]
    }
