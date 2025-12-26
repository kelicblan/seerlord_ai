from typing import Optional, Tuple
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger
from sqlalchemy import select
from server.core.config import settings
from server.core.database import SessionLocal
from server.models.api_key import ApiKey


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Skip auth for public endpoints, docs, and static files
        if request.url.path in ["/docs", "/redoc", "/openapi.json", "/health", "/", "/api/v1/login/access-token", "/api/v1/setup/initialize"]:
            return await call_next(request)
            
        # 2. Skip static assets
        if request.url.path.startswith("/assets/") or request.url.path.endswith((".js", ".css", ".png", ".ico", ".json", ".html")):
             return await call_next(request)

        # 3. Identify Whitelisted Paths (Optional Auth)
        # These paths can work without an API Key (e.g. using Bearer token, or completely public)
        # But if an API Key IS provided, we should process it to establish Tenant Context.
        is_whitelisted = False
        if request.url.path in ["/api/v1/users/me", "/api/v1/mcp/status", "/api/v1/plugins", "/api/v1/files/upload", "/api/v1/agent/stream_events"]:
            is_whitelisted = True
        elif request.url.path.startswith("/api/v1/agent/") and request.url.path.endswith("/graph"):
            is_whitelisted = True
        elif not request.url.path.startswith("/api/") and not request.url.path.startswith("/agent"):
            # Frontend routes
            is_whitelisted = True

        # 4. Attempt Authentication via X-API-Key
        api_key = request.headers.get("X-API-Key")
        
        if api_key:
            # Validate API Key
            try:
                async with SessionLocal() as session:
                    stmt = select(ApiKey).where(ApiKey.key == api_key, ApiKey.is_active == True)
                    result = await session.execute(stmt)
                    key_obj = result.scalars().first()
                    
                    if key_obj:
                        request.state.tenant_id = str(key_obj.user_id)
                        request.state.app_name = key_obj.name or "External App"
                    else:
                        # Invalid Key
                        if settings.ALLOW_DEFAULT_TENANT_FALLBACK:
                            logger.warning(f"Invalid API Key: {api_key}. Using default tenant context (Fallback Enabled).")
                            request.state.tenant_id = "tenant-admin"
                            request.state.app_name = "Default Admin Context"
                        elif not is_whitelisted:
                             return JSONResponse(
                                 status_code=403, 
                                 content={"detail": "Invalid API Key"}
                             )
            except Exception as e:
                logger.error(f"Auth DB Error: {e}")
                # If DB fails, try fallback if enabled
                if settings.ALLOW_DEFAULT_TENANT_FALLBACK:
                    logger.warning("Auth DB failed. Using default tenant context (Fallback Enabled).")
                    request.state.tenant_id = "tenant-admin"
                    request.state.app_name = "Default Admin Context"
                elif not is_whitelisted:
                    return JSONResponse(status_code=500, content={"detail": "Authentication Error"})

        # 5. Fallback if no key provided
        elif settings.ALLOW_DEFAULT_TENANT_FALLBACK:
             # logger.warning("Missing X-API-Key header. Using default tenant context (Fallback Enabled).")
             # Reduce log noise for whitelisted paths or frequent polling
             request.state.tenant_id = "tenant-admin"
             request.state.app_name = "Default Admin Context"

        # 6. Final Access Check
        if hasattr(request.state, "tenant_id"):
             logger.debug(f"Authorized Request for Tenant: {request.state.tenant_id} ({request.state.app_name})")
             return await call_next(request)
        
        if is_whitelisted:
             return await call_next(request)

        return JSONResponse(
             status_code=401,
             content={"detail": "Missing X-API-Key header and fallback is disabled."}
        )

def get_current_tenant_id(request: Request) -> str:
    """Dependency to get the current tenant ID from request state."""
    if not hasattr(request.state, "tenant_id"):
        raise HTTPException(status_code=401, detail="Tenant context missing")
    return request.state.tenant_id

def get_current_tenant_id_optional(request: Request) -> str:
    """
    Dependency to get the current tenant ID from request state, 
    or return 'public' if missing (for whitelisted endpoints).
    """
    if hasattr(request.state, "tenant_id"):
        return request.state.tenant_id
    return "public"

