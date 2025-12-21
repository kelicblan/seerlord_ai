from typing import Optional, Tuple
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger

# In a real scenario, this would come from a database
MOCK_TENANT_DB = {
    "sk-construction-app": {"tenant_id": "tenant-001", "name": "Construction Expert App"},
    "sk-learning-tutor": {"tenant_id": "tenant-002", "name": "Personal Tutor App"},
    "sk-admin-test": {"tenant_id": "tenant-admin", "name": "Admin Test"}
}

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints, docs, and static files
        # Also skip Login APIs which use their own Auth mechanism
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health", "/", "/api/v1/login/access-token", "/api/v1/setup/initialize"]:
            return await call_next(request)
            
        # Also skip static assets if they are served under root but with extensions or specific paths
        # This is a simple heuristic; production might check exact static paths
        if request.url.path.startswith("/assets/") or request.url.path.endswith((".js", ".css", ".png", ".ico", ".json", ".html")):
             return await call_next(request)

        # Only enforce Auth on /api/ routes or agent invocation routes
        # Skip /api/v1/users/me because it uses Bearer Token
        if request.url.path == "/api/v1/users/me":
            return await call_next(request)

        if not request.url.path.startswith("/api/") and not request.url.path.startswith("/agent"):
             # Allow other paths (likely frontend routes handled by SPA fallback)
             return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
             # Fallback for development convenience, or reject
             # For now, we reject strict B2B APIs
             return JSONResponse(
                 status_code=401, 
                 content={"detail": "Missing X-API-Key header"}
             )
        
        tenant_info = MOCK_TENANT_DB.get(api_key)
        if not tenant_info:
            return JSONResponse(
                 status_code=403, 
                 content={"detail": "Invalid API Key"}
             )
             
        # Inject Tenant ID into Request State
        request.state.tenant_id = tenant_info["tenant_id"]
        request.state.app_name = tenant_info["name"]
        
        logger.debug(f"Authorized Request for Tenant: {tenant_info['tenant_id']} ({tenant_info['name']})")
        
        response = await call_next(request)
        return response

def get_current_tenant_id(request: Request) -> str:
    """Dependency to get the current tenant ID from request state."""
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(status_code=401, detail="Tenant context missing")
    return request.state.tenant_id
