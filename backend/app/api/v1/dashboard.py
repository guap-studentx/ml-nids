from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user, get_dashboard_service
from app.models.user import User
from app.schemas.analytics import DashboardSummary, DashboardTimeseries

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    dashboard_service: Annotated[object, Depends(get_dashboard_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> DashboardSummary:
    return await dashboard_service.summary()


@router.get("/timeseries", response_model=DashboardTimeseries)
async def dashboard_timeseries(
    dashboard_service: Annotated[object, Depends(get_dashboard_service)],
    _: Annotated[User, Depends(get_current_user)],
    period: Annotated[str, Query(pattern=r"^\d+h$")] = "24h",
) -> DashboardTimeseries:
    return await dashboard_service.timeseries(period)
