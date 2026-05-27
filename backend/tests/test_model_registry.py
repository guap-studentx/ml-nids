from pathlib import Path

import pytest

from app.services.model_registry import ModelRegistryService


class FakeModelRepository:
    def __init__(self):
        self.items = []

    async def upsert_manifest_model(self, **kwargs):
        self.items.append(kwargs)


@pytest.mark.asyncio
async def test_load_manifest_reads_all_artifacts():
    repo = FakeModelRepository()
    service = ModelRegistryService(repo)
    artifacts_dir = Path(__file__).resolve().parents[2] / "artifacts"

    loaded = await service.load_manifest(artifacts_dir, default_model_id="xgboost")

    assert loaded == 8
    assert len(repo.items) == 8
    assert [item for item in repo.items if item["is_default"]][0]["model_id"] == "xgboost"
