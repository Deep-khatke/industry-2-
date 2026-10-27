"""Authentication and user identity API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user
from ..auth.service import create_access_token, verify_password
from ..database import get_db

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2)
    password: str = Field(..., min_length=4)


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
    """Authenticate user with username and password, returns JWT token."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
            )

        if not verify_password(req.password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
            )

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
