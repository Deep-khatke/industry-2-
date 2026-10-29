"""Authentication and user identity API endpoints (Hardened)."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user
from ..auth.service import (
    create_access_token,
    is_rate_limited,
    record_failed_attempt,
    reset_failed_attempts,
    revoke_token,
    verify_password,
)
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])

DEMO_USERNAMES = {
    "admin_alpha", "analyst_alpha", "responder_alpha", "viewer_alpha",
    "analyst_bravo", "responder_bravo", "platform_admin",
}


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=4, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    tenant_id: str | None
    role: str
    full_name: str


@router.post("/token", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    """Authenticate user with username and password, returns JWT token with brute-force protection."""
    # Check rate limiting / brute-force protection
    if is_rate_limited(req.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts. Account temporarily locked; please retry after 60 seconds.",
        )

    # In non-development mode, reject demo accounts
    if not settings.allow_demo_credentials and req.username in DEMO_USERNAMES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demonstration accounts are strictly prohibited outside DEVELOPMENT mode.",
        )

    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
        if not row:
            record_failed_attempt(req.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
            )

        if not verify_password(req.password, row["password_hash"]):
            count = record_failed_attempt(req.username)
            remaining = max(0, 5 - count)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect username or password. Remaining attempts before lockout: {remaining}",
            )

        # Successful login: reset failed attempts
        reset_failed_attempts(req.username)

        token = create_access_token(
            user_id=row["user_id"],
            username=row["username"],
            tenant_id=row["tenant_id"],
            role=row["role"],
        )

        return TokenResponse(
            access_token=token,
            user_id=row["user_id"],
            username=row["username"],
            tenant_id=row["tenant_id"],
            role=row["role"],
            full_name=row["full_name"],
        )


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """Revoke caller's current JWT token session."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid Bearer token required to logout.",
        )
    token = authorization.split()[1]
    revoke_token(token)
    return {"status": "SUCCESS", "message": "Session terminated and access token successfully revoked."}


@router.get("/me")
def get_me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Retrieve identity and permissions for the authenticated caller."""
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "tenant_id": user["tenant_id"],
        "role": user["role"],
        "full_name": user["full_name"],
        "created_at": user["created_at"],
    }
