import time
from typing import Dict, Optional, Tuple, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

class InMemoryStore:
    def __init__(self):
        self.store: Dict[str, Dict[str, Tuple[int, float]]] = {}
        
    def get_bucket(self, key: str, limit_id: str) -> Tuple[int, float]:
        """Get current rate limit bucket (count, reset_time)"""
        if key not in self.store:
            self.store[key] = {}
        if limit_id not in self.store[key]:
            self.store[key][limit_id] = (0, time.time() + 60)  # 60 second window
        return self.store[key][limit_id]
        
    def increment(self, key: str, limit_id: str) -> Tuple[int, float]:
        """Increment count and return new values"""
        count, reset_at = self.get_bucket(key, limit_id)
        if reset_at <= time.time():
            count = 0
            reset_at = time.time() + 60  # 60 second window
        count += 1
        self.store[key][limit_id] = (count, reset_at)
        return (count, reset_at)
        
    def reset(self, key: str, limit_id: str) -> None:
        """Reset counter for a specific key and limit_id"""
        if key in self.store and limit_id in self.store[key]:
            self.store[key][limit_id] = (0, time.time() + 60)

store = InMemoryStore()

def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    if not request.client or not request.client.host:
        return "unknown"
    return request.client.host

def create_rate_limiter(limit: int, window: int = 60, limit_id: str = "default"):
    """
    Create a rate limiter dependency that can be used in FastAPI endpoints
    
    Args:
        limit: Maximum number of requests allowed in the window
        window: Time window in seconds
        limit_id: Identifier for this rate limit
        
    Returns:
        FastAPI dependency function
    """
    async def rate_limit_dependency(request: Request, response: Response):
        client_ip = get_client_ip(request)
        key = f"{client_ip}"
        
        count, reset_at = store.increment(key, limit_id)
        
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        response.headers["X-RateLimit-Reset"] = str(int(reset_at))
        
        if count > limit:
            retry_after = int(reset_at - time.time())
            response.headers["Retry-After"] = str(max(0, retry_after))
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds."
            )
            
    return rate_limit_dependency

auth_rate_limiter = create_rate_limiter(limit=5, window=60, limit_id="auth")
general_rate_limiter = create_rate_limiter(limit=60, window=60, limit_id="general")
