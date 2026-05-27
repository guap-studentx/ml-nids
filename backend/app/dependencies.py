from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.exceptions import AuthError, PermissionDeniedError
from app.models.user import User
from app.repositories.agent_repository import AgentRepository
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.flow_repository import FlowRepository
from app.repositories.live_session_repository import LiveSessionRepository
from app.repositories.model_repository import ModelRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.security import decode_access_token
from app.services.agent_service import AgentService
from app.services.auth_service import AuthService
from app.services.capture_service import CaptureService
from app.services.flow_service import FlowService
from app.services.live_session_service import LiveSessionService
from app.services.model_service import ModelService
from app.services.model_registry import ModelRegistryService
from app.services.report_service import ReportService

bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> UserRepository:
    return UserRepository(session)


def get_agent_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> AgentRepository:
    return AgentRepository(session)


def get_model_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> ModelRepository:
    return ModelRepository(session)


def get_capture_session_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CaptureSessionRepository:
    return CaptureSessionRepository(session)


def get_live_session_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LiveSessionRepository:
    return LiveSessionRepository(session)


def get_flow_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> FlowRepository:
    return FlowRepository(session)


def get_report_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> ReportRepository:
    return ReportRepository(session)


def get_auth_service(users: Annotated[UserRepository, Depends(get_user_repository)]) -> AuthService:
    return AuthService(users)


def get_agent_service(agents: Annotated[AgentRepository, Depends(get_agent_repository)]) -> AgentService:
    return AgentService(agents)


def get_model_registry_service(
    models: Annotated[ModelRepository, Depends(get_model_repository)],
) -> ModelRegistryService:
    return ModelRegistryService(models)


def get_model_service(models: Annotated[ModelRepository, Depends(get_model_repository)]) -> ModelService:
    return ModelService(models)


def get_capture_service(
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    models: Annotated[ModelRepository, Depends(get_model_repository)],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> CaptureService:
    return CaptureService(captures, models, agents)


def get_live_session_service(
    live_sessions: Annotated[LiveSessionRepository, Depends(get_live_session_repository)],
    models: Annotated[ModelRepository, Depends(get_model_repository)],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
) -> LiveSessionService:
    return LiveSessionService(live_sessions, models, agents)


def get_flow_service(
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    flows: Annotated[FlowRepository, Depends(get_flow_repository)],
) -> FlowService:
    from app.config import get_settings

    return FlowService(captures, flows, get_settings().captures_dir)


def get_capture_analytics_service(
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    flows: Annotated[FlowRepository, Depends(get_flow_repository)],
):
    from app.config import get_settings
    from app.services.capture_analytics_service import CaptureAnalyticsService

    return CaptureAnalyticsService(captures, flows, get_settings().captures_dir)


def get_report_service(
    reports: Annotated[ReportRepository, Depends(get_report_repository)],
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    flows: Annotated[FlowRepository, Depends(get_flow_repository)],
) -> ReportService:
    from app.config import get_settings
    from app.services.capture_analytics_service import CaptureAnalyticsService

    settings = get_settings()
    analytics = CaptureAnalyticsService(captures, flows, settings.captures_dir)
    return ReportService(reports, analytics, settings.reports_dir)


def get_dashboard_service(
    captures: Annotated[CaptureSessionRepository, Depends(get_capture_session_repository)],
    models: Annotated[ModelRepository, Depends(get_model_repository)],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
):
    from app.services.dashboard_service import DashboardService

    return DashboardService(captures, models, agents)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    if credentials is None:
        raise AuthError()
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise AuthError() from exc
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError()
    user = await users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthError()
    return user


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "admin":
        raise PermissionDeniedError()
    return current_user
