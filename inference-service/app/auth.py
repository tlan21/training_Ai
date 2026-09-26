"""Bearer auth — mọi request kèm Authorization: Bearer ${AI_SERVICE_KEY} (master plan §2.4)."""

from fastapi import Header, HTTPException, status

from .config import settings


async def require_bearer(authorization: str = Header(default="")) -> None:
    """Xác thực Bearer key. Sai/thiếu → 401 với error envelope."""
    prefix = "Bearer "
    if not authorization.startswith(prefix) or authorization[len(prefix):] != settings.ai_service_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or missing AI service key"},
        )
