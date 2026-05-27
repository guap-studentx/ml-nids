from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_model import MLModel


class ModelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, active_only: bool = False) -> list[MLModel]:
        stmt = select(MLModel).order_by(MLModel.is_default.desc(), MLModel.display_name)
        if active_only:
            stmt = stmt.where(MLModel.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        result = await self.session.execute(select(MLModel).where(MLModel.is_active.is_(True)))
        return len(result.scalars().all())

    async def get_by_model_id(self, model_id: str) -> MLModel | None:
        result = await self.session.execute(select(MLModel).where(MLModel.model_id == model_id))
        return result.scalar_one_or_none()

    async def get(self, model_id: uuid.UUID) -> MLModel | None:
        result = await self.session.execute(select(MLModel).where(MLModel.id == model_id))
        return result.scalar_one_or_none()

    async def unset_default(self) -> None:
        await self.session.execute(update(MLModel).values(is_default=False).where(MLModel.is_default.is_(True)))
        await self.session.flush()

    async def delete(self, model: MLModel) -> None:
        await self.session.delete(model)
        await self.session.flush()

    async def create_uploaded_model(
        self,
        *,
        model_id: str,
        display_name: str,
        model_class_name: str,
        score_type: str,
        decision_threshold: float,
        features: list[str],
        metrics_test: dict | None,
        artifact_path: str,
        uploaded_by: uuid.UUID | None,
    ) -> MLModel:
        model = MLModel(
            model_id=model_id,
            display_name=display_name,
            model_class_name=model_class_name,
            score_type=score_type,
            decision_threshold=decision_threshold,
            features=features,
            metrics_test=metrics_test,
            artifact_path=artifact_path,
            uploaded_by=uploaded_by,
            is_active=True,
            is_default=False,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def upsert_manifest_model(
        self,
        *,
        model_id: str,
        display_name: str,
        model_class_name: str,
        score_type: str,
        decision_threshold: float,
        features: list[str],
        metrics_test: dict,
        artifact_path: str,
        is_default: bool,
    ) -> MLModel:
        model = await self.get_by_model_id(model_id)
        if model is None:
            model = MLModel(model_id=model_id, display_name=display_name, artifact_path=artifact_path)
            self.session.add(model)

        model.display_name = display_name
        model.model_class_name = model_class_name
        model.score_type = score_type
        model.decision_threshold = decision_threshold
        model.features = features
        model.metrics_test = metrics_test
        model.artifact_path = artifact_path
        model.is_active = True
        model.is_default = is_default
        await self.session.flush()
        return model
