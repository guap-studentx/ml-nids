import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.inference.postfilter import apply_postfilter
from app.exceptions import ModelNotFoundError
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.flow_repository import FlowRepository
from app.repositories.model_repository import ModelRepository
from app.services.flow_storage_service import FlowStorageService
from app.services.inference_service import InferenceService


class OfflineCsvService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        captures_dir: Path,
        models_dir: Path,
    ):
        self.session = session
        self.captures = CaptureSessionRepository(session)
        self.models = ModelRepository(session)
        self.flow_storage = FlowStorageService(FlowRepository(session), captures_dir)
        self.inference = InferenceService(models_dir)

    async def process(self, capture_id: uuid.UUID, csv_path: Path) -> None:
        capture = await self.captures.get(capture_id)
        if capture is None:
            return

        try:
            await self.captures.mark_running(capture, source_filename=csv_path.name)
            await self.session.commit()

            model = await self.models.get(capture.model_id)
            if model is None:
                raise ModelNotFoundError()
            df_raw = pd.read_csv(csv_path)
            df_filtered = apply_postfilter(df_raw)
            results = await self.inference.predict(model, df_filtered)
            await self.flow_storage.store_results(capture.id, results)
            await self.captures.mark_completed(
                capture,
                flows_total=int(len(results)),
                flows_anomaly=int(results["prediction"].sum()),
            )
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            capture = await self.captures.get(capture_id)
            if capture is not None:
                await self.captures.mark_failed(capture, error_message=str(exc))
                await self.session.commit()
