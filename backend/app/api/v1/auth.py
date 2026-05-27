from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, auth_service: Annotated[AuthService, Depends(get_auth_service)]) -> TokenResponse:
    user, token = await auth_service.authenticate(payload.username, payload.password)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", response_model=UserRead)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
