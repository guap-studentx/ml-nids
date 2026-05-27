import asyncio
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ModelNotFoundError
from app.inference.postfilter import apply_postfilter
from app.repositories.capture_session_repository import CaptureSessionRepository
from app.repositories.flow_repository import FlowRepository
from app.repositories.live_session_repository import LiveSessionRepository
from app.repositories.model_repository import ModelRepository
from app.services.flow_storage_service import FlowStorageService
from app.services.inference_service import InferenceService
from app.services.nfstream_settings import NFSTREAM_OFFLINE_SETTINGS


class OfflinePcapService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        captures_dir: Path,
        models_dir: Path,
    ):
        self.session = session
        self.captures = CaptureSessionRepository(session)
        self.live_sessions = LiveSessionRepository(session)
        self.models = ModelRepository(session)
        self.flow_storage = FlowStorageService(FlowRepository(session), captures_dir)
        self.inference = InferenceService(models_dir)

    async def process(self, capture_id: uuid.UUID, pcap_path: Path) -> None:
        capture = await self.captures.get(capture_id)
        if capture is None:
            return

        try:
            await self.captures.mark_running(capture, source_filename=pcap_path.name)
            await self.session.commit()

            model = await self.models.get(capture.model_id)
            if model is None:
                raise ModelNotFoundError()

            df_raw = await asyncio.to_thread(self._pcap_to_dataframe, pcap_path)
            df_filtered = apply_postfilter(df_raw)
            results = await self.inference.predict(model, df_filtered)
            await self.flow_storage.store_results(capture.id, results)
            await self.captures.mark_completed(
                capture,
                flows_total=int(len(results)),
                flows_anomaly=int(results["prediction"].sum()),
            )
            if capture.live_session_id is not None:
                flows_total, flows_anomaly = await self.captures.aggregate_live_session(capture.live_session_id)
                live_session = await self.live_sessions.get(capture.live_session_id)
                if live_session is not None:
                    await self.live_sessions.update_aggregates(
                        live_session,
                        flows_total=flows_total,
                        flows_anomaly=flows_anomaly,
                    )
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            capture = await self.captures.get(capture_id)
            if capture is not None:
                await self.captures.mark_failed(capture, error_message=str(exc))
                await self.session.commit()

    def _pcap_to_dataframe(self, pcap_path: Path) -> pd.DataFrame:
        try:
            from nfstream import NFStreamer
        except ImportError as exc:
            raise RuntimeError("NFStream is not installed; rebuild backend with the ml dependencies") from exc

        streamer = NFStreamer(source=str(pcap_path), **NFSTREAM_OFFLINE_SETTINGS)
        df = streamer.to_pandas()
        if df is None:
            return pd.DataFrame()
        return df
