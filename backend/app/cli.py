import argparse
import asyncio
from pathlib import Path

from app.config import get_settings
from app.database import async_session_factory
from app.repositories.model_repository import ModelRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.model_registry import ModelRegistryService


async def init_admin() -> None:
    settings = get_settings()
    async with async_session_factory() as session:
        service = AuthService(UserRepository(session))
        user = await service.ensure_admin(settings.admin_username, settings.admin_password)
        await session.commit()
        print(f"Admin user ready: {user.username}")


async def load_models(path: str) -> None:
    settings = get_settings()
    async with async_session_factory() as session:
        service = ModelRegistryService(ModelRepository(session))
        loaded = await service.load_manifest(Path(path), settings.default_model_id)
        await session.commit()
        print(f"Loaded models: {loaded}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-admin")
    load_models_parser = subparsers.add_parser("load-models")
    load_models_parser.add_argument("path")
    args = parser.parse_args()

    if args.command == "init-admin":
        asyncio.run(init_admin())
    elif args.command == "load-models":
        asyncio.run(load_models(args.path))


if __name__ == "__main__":
    main()
