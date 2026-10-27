"""FastAPI authentication and authorization dependencies."""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Header, HTTPException, status

from ..database import get_db
from .service import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Dependency that extracts, verifies, and returns the current authenticated user."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Must be 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    try:
        payload = decode_access_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user_id = payload.get("sub")
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in system.",
            )
        return dict(row)


def require_role(*allowed_roles: str) -> Callable[..., dict[str, Any]]:
    """Dependency factory checking that current user has one of the required roles."""

    def role_checker(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user["role"] not in allowed_roles and user["role"] != "PLATFORM_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires one of {allowed_roles}, but caller has role '{user['role']}'.",
            )
        return user

    return role_checker


def verify_tenant_boundary(user: dict[str, Any], requested_tenant_id: str) -> None:
    """Enforces strict multi-tenant boundary. Raises 403 on cross-tenant access attempt."""
    if user["role"] in ("PLATFORM_ADMIN", "PLATFORM_AUDITOR"):
        return
    if user.get("tenant_id") != requested_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cross-tenant access violation: Caller tenant '{user.get('tenant_id')}' cannot access '{requested_tenant_id}'.",
        )
