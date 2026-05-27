import uuid
from datetime import UTC
from pathlib import Path
from typing import Any

import pandas as pd

from app.models.flow import Flow
from app.repositories.flow_repository import FlowRepository


class FlowStorageService:
    def __init__(self, flows: FlowRepository, captures_dir: Path, benign_sample_rate: int = 100):
        self.flows = flows
        self.captures_dir = captures_dir
        self.benign_sample_rate = benign_sample_rate

    async def store_results(self, session_id: uuid.UUID, results: pd.DataFrame) -> Path:
        capture_dir = self.captures_dir / str(session_id)
        capture_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = capture_dir / "flows.parquet"
        results.to_parquet(parquet_path, index=False)

        rows_to_store = results[
            (results["prediction"] == 1)
            | ((results["prediction"] == 0) & (results.index % self.benign_sample_rate == 0))
        ]
        await self.flows.add_many([self._row_to_flow(session_id, row) for _, row in rows_to_store.iterrows()])
        return parquet_path

    def _row_to_flow(self, session_id: uuid.UUID, row: pd.Series) -> Flow:
        return Flow(
            session_id=session_id,
            src_ip=self._optional_str(row, "src_ip"),
            dst_ip=self._optional_str(row, "dst_ip"),
            src_port=self._optional_int(row, "src_port"),
            dst_port=self._optional_int(row, "dst_port"),
            protocol=self._optional_int(row, "protocol"),
            bidirectional_duration_ms=self._optional_int(row, "bidirectional_duration_ms"),
            bidirectional_packets=self._optional_int(row, "bidirectional_packets"),
            bidirectional_bytes=self._optional_int(row, "bidirectional_bytes"),
            anomaly_score=float(row["anomaly_score"]),
            prediction=int(row["prediction"]),
            flow_features=self._jsonable_dict(row.to_dict()),
            flow_timestamp=self._optional_timestamp(row),
        )

    def _optional_str(self, row: pd.Series, key: str) -> str | None:
        value = row.get(key)
        if pd.isna(value):
            return None
        return str(value)

    def _optional_int(self, row: pd.Series, key: str) -> int | None:
        value = row.get(key)
        if pd.isna(value):
            return None
        return int(value)

    def _optional_timestamp(self, row: pd.Series):
        for key in ("flow_timestamp", "bidirectional_first_seen_ms", "src2dst_first_seen_ms", "dst2src_first_seen_ms"):
            if key in row and not pd.isna(row[key]):
                value = row[key]
                if isinstance(value, (int, float)) and value <= 0:
                    continue
                if key.endswith("_ms") and isinstance(value, (int, float)):
                    return pd.to_datetime(value, unit="ms", utc=True).to_pydatetime()
                return pd.to_datetime(value, utc=True).to_pydatetime()
        return None

    def _jsonable_dict(self, values: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for key, value in values.items():
            if pd.isna(value):
                result[key] = None
            elif hasattr(value, "item"):
                result[key] = value.item()
            elif hasattr(value, "isoformat"):
                result[key] = value.astimezone(UTC).isoformat() if getattr(value, "tzinfo", None) else value.isoformat()
            else:
                result[key] = value
        return result
