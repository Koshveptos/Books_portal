from auth import auth_backend, current_active_user
from core.database import get_db
from fastapi import Depends, HTTPException, status
from models.user import User
from schemas.user import LogoutResponse, TokenResponse
from sqlalchemy.ext.asyncio import AsyncSession


async def refresh_token(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        new_access_token = await auth_backend.get_strategy().write_token(user)
        return TokenResponse(access_token=new_access_token, token_type="bearer")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


async def logout(user: User = Depends(current_active_user)) -> LogoutResponse:
    return LogoutResponse(detail="Successfully logged out")


async def protected_route(user: User = Depends(current_active_user)) -> dict:
    return {"user": user.email}
