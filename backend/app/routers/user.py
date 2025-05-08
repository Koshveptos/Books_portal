from auth import auth_backend, current_active_user, fastapi_users
from core.database import get_db
from fastapi import Depends, HTTPException, status
from fastapi_users.exceptions import UserAlreadyExists
from models.user import User
from schemas.user import LogoutResponse, TokenResponse, UserCreate, UserRead
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
    return {
        "user": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "is_verified": user.is_verified,
        "is_moderator": user.is_moderator,
    }


async def register(
    user_create: UserCreate,
    user_manager=Depends(fastapi_users.get_user_manager),
) -> UserRead:
    try:
        created_user = await user_manager.create(user_create)
        return UserRead.model_validate(created_user)
    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        )
