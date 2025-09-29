# server/api/neurolex_xref_routes.py
from fastapi import APIRouter, HTTPException
from .db import pg_read

router = APIRouter(prefix="/api/neurolex", tags=["neurolex-xref"])

@router.get("/xref/{ilx_id}")
def get_xrefs(ilx_id: str):
    """
    Return all external cross-references for an ILX term.
    """
    rows = pg_read(
        """
        SELECT system, code
        FROM ontology.neurolex_xref
        WHERE ilx_id = %s
        ORDER BY system, code
        """,
        (ilx_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No xrefs found for ilx_id")
    return {"ilx_id": ilx_id, "xrefs": rows}

@router.get("/map/{system}/{code}")
def map_system_code(system: str, code: str):
    """
    Map an external code (e.g., ICD10/G12.2) to ILX terms.
    """
    rows = pg_read(
        """
        SELECT x.ilx_id, n.label
        FROM ontology.neurolex_xref x
        JOIN ontology.neurolex n USING (ilx_id)
        WHERE x.system = %s AND x.code = %s
        ORDER BY n.label
        """,
        (system, code),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No ILX mapping for system/code")
    return {"system": system, "code": code, "matches": rows}

@router.get("/xref/by-system/{system}")
def list_codes_for_system(system: str, limit: int = 100, offset: int = 0):
    """
    List codes we have for a given coding system (paged).
    """
    rows = pg_read(
        """
        SELECT code, COUNT(*) AS n_terms
        FROM ontology.neurolex_xref
        WHERE system = %s
        GROUP BY code
        ORDER BY n_terms DESC, code
        LIMIT %s OFFSET %s
        """,
        (system, limit, offset),
    )
    return {"system": system, "items": rows, "limit": limit, "offset": offset}

