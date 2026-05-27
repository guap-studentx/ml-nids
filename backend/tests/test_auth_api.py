import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.dependencies import get_auth_service
from app.exceptions import AuthError


class FakeAuthService:
    async def authenticate(self, username: str, password: str):
        if username != "admin" or password != "admin":
            raise AuthError()
        user = SimpleNamespace(id=uuid.uuid4(), username="admin", role="admin", created_at=datetime.now(UTC), is_active=True)
        return user, "fake-token"


def test_login_returns_token(client):
    client.app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()

    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})

    assert response.status_code == 200
    assert response.json() == {"access_token": "fake-token", "token_type": "bearer", "role": "admin"}


def test_login_rejects_wrong_password(client):
    client.app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()

    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
