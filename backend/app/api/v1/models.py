import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.dependencies import get_current_user, get_model_service, require_admin
from app.models.user import User
from app.schemas.ml_model import MLModelDetail, MLModelRead, MLModelUpdate
from app.services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[MLModelRead])
async def list_models(
    model_service: Annotated[ModelService, Depends(get_model_service)],
    _: Annotated[User, Depends(get_current_user)],
) -> list:
    return await model_service.list()


async def save_upload(file: UploadFile, upload_path: Path) -> None:
    with upload_path.open("wb") as target:
        while chunk := await file.read(1024 * 1024):
            target.write(chunk)


@router.post("/upload", response_model=MLModelRead, status_code=status.HTTP_201_CREATED)
async def upload_model(
    model_service: Annotated[ModelService, Depends(get_model_service)],
    current_user: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File()],
    model_id: Annotated[str | None, Form()] = None,
    display_name: Annotated[str | None, Form()] = None,
) -> MLModelRead:
    settings = get_settings()
    upload_dir = settings.uploads_dir / "model_artifacts"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(file.filename or "model.joblib").name
    upload_path = upload_dir / f"{uuid.uuid4()}_{safe_filename}"
    await save_upload(file, upload_path)
    model = await model_service.create_from_artifact(
        artifact_path=upload_path,
        uploaded_by=current_user.id,
        model_id=model_id,
        display_name=display_name,
    )
    await session.commit()
    await session.refresh(model)
    return model


@router.get("/{model_id}", response_model=MLModelDetail)
async def get_model(
    model_id: uuid.UUID,
    model_service: Annotated[ModelService, Depends(get_model_service)],
    _: Annotated[User, Depends(get_current_user)],
):
    model, details = await model_service.detail(model_id)
    data = MLModelRead.model_validate(model).model_dump()
    return MLModelDetail(**data, **details)


@router.patch("/{model_id}", response_model=MLModelRead)
async def update_model(
    model_id: uuid.UUID,
    payload: MLModelUpdate,
    model_service: Annotated[ModelService, Depends(get_model_service)],
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    model = await model_service.update(
        model_id,
        is_active=payload.is_active,
        is_default=payload.is_default,
    )
    await session.commit()
    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: uuid.UUID,
    model_service: Annotated[ModelService, Depends(get_model_service)],
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await model_service.delete(model_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
