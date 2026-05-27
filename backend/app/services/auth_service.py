from app.exceptions import AuthError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    async def authenticate(self, username: str, password: str) -> tuple[User, str]:
        user = await self.users.get_by_username(username)
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise AuthError()
        token = create_access_token(str(user.id), {"role": user.role})
        return user, token

    async def ensure_admin(self, username: str, password: str) -> User:
        user = await self.users.get_by_username(username)
        if user is not None:
            return user
        return await self.users.create(username=username, password_hash=hash_password(password), role="admin")
