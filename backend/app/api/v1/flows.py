import uuid
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.dependencies import get_current_user, get_flow_service
from app.models.user import User
from app.schemas.flow import FlowDetailResponse, FlowListResponse, FlowRead
from app.services.flow_service import FlowService

router = APIRouter(prefix="/captures/{capture_id}/flows", tags=["flows"])


@router.get("", response_model=FlowListResponse)
async def list_flows(
    capture_id: uuid.UUID,
    flow_service: Annotated[FlowService, Depends(get_flow_service)],
    _: Annotated[User, Depends(get_current_user)],
    prediction: Annotated[int | None, Query(ge=0, le=1)] = None,
    min_score: Annotated[float | None, Query(ge=0)] = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    protocol: Annotated[int | None, Query(ge=0, le=255)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FlowListResponse:
    flows, total = await flow_service.list(
        session_id=capture_id,
        prediction=prediction,
        min_score=min_score,
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol=protocol,
        limit=limit,
        offset=offset,
    )
    return FlowListResponse(items=flows, total=total, limit=limit, offset=offset)


@router.get("/top", response_model=list[FlowRead])
async def top_flows(
    capture_id: uuid.UUID,
    flow_service: Annotated[FlowService, Depends(get_flow_service)],
    _: Annotated[User, Depends(get_current_user)],
    n: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list:
    return await flow_service.top(session_id=capture_id, n=n)


@router.get("/export")
async def export_flows(
    capture_id: uuid.UUID,
    flow_service: Annotated[FlowService, Depends(get_flow_service)],
    _: Annotated[User, Depends(get_current_user)],
    format: Literal["parquet", "csv"] = "parquet",
) -> FileResponse:
    export_path = await flow_service.export_path(session_id=capture_id, export_format=format)
    return FileResponse(
        path=export_path,
        media_type=_media_type(export_path),
        filename=f"{capture_id}_flows{export_path.suffix}",
    )


def _media_type(path: Path) -> str:
    if path.suffix == ".csv":
        return "text/csv"
    return "application/vnd.apache.parquet"


@router.get("/{flow_id}", response_model=FlowDetailResponse)
async def get_flow(
    capture_id: uuid.UUID,
    flow_id: uuid.UUID,
    flow_service: Annotated[FlowService, Depends(get_flow_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> FlowDetailResponse:
    flow = await flow_service.get(session_id=capture_id, flow_id=flow_id)
    return FlowDetailResponse(flow=flow, explanation=flow_service.explain(flow))
