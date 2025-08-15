
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="MongoDB implementation deprecated. Use server.api.auth_routes_postgres for PostgreSQL auth."
)
