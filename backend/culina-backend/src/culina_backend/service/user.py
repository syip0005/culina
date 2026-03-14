"""UserService — business logic for user management."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from culina_backend.database.models import UserModel, UserSettings as UserSettingsORM
from culina_backend.model.user import User, UserFilter, UserSettings
from culina_backend.service.converters import (
    user_from_orm,
    user_settings_to_orm,
    user_to_orm,
)
from culina_backend.service.errors import DuplicateError, NotFoundError


class UserService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create_user(self, data: User) -> User:
        orm = user_to_orm(data)
        settings_orm = user_settings_to_orm(data.settings or UserSettings(), data.id)
        async with self._session_factory() as session:
            session.add(orm)
            session.add(settings_orm)
            try:
                await session.flush()
            except IntegrityError as exc:
                raise DuplicateError(
                    f"User with external_id={data.external_id!r} already exists"
                ) from exc
            await session.commit()

            # Reload with settings eagerly loaded
            q = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(UserModel.id == orm.id)
            )
            result = await session.execute(q)
            return user_from_orm(result.scalar_one())

    async def get_user(self, user_id: UUID) -> User | None:
        async with self._session_factory() as session:
            q = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(UserModel.id == user_id, UserModel.deleted_at.is_(None))
            )
            result = await session.execute(q)
            row = result.scalar_one_or_none()
            return user_from_orm(row) if row else None

    async def get_user_by_email(self, email: str) -> User | None:
        async with self._session_factory() as session:
            q = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(UserModel.email == email, UserModel.deleted_at.is_(None))
            )
            result = await session.execute(q)
            row = result.scalar_one_or_none()
            return user_from_orm(row) if row else None

    async def get_user_by_external_id(self, external_id: str) -> User | None:
        async with self._session_factory() as session:
            q = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(
                    UserModel.external_id == external_id,
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await session.execute(q)
            row = result.scalar_one_or_none()
            return user_from_orm(row) if row else None

    async def user_exists(self, user_id: UUID) -> bool:
        return await self.get_user(user_id) is not None

    async def list_users(
        self,
        filter: UserFilter | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[User]:
        filter = filter or UserFilter()
        async with self._session_factory() as session:
            q = select(UserModel).options(selectinload(UserModel.settings))

            if not filter.include_deleted:
                q = q.where(UserModel.deleted_at.is_(None))
            if filter.email:
                q = q.where(UserModel.email.ilike(f"%{filter.email}%"))
            if filter.display_name:
                q = q.where(UserModel.display_name.ilike(f"%{filter.display_name}%"))

            q = q.order_by(UserModel.created_at).offset(offset).limit(limit)
            result = await session.execute(q)
            return [user_from_orm(row) for row in result.scalars()]

    async def update_user(self, user_id: UUID, data: dict) -> User:
        allowed = {"email", "display_name"}
        async with self._session_factory() as session:
            q = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(UserModel.id == user_id, UserModel.deleted_at.is_(None))
            )
            result = await session.execute(q)
            row = result.scalar_one_or_none()
            if row is None:
                raise NotFoundError(f"User {user_id} not found")

            for key, value in data.items():
                if key in allowed:
                    setattr(row, key, value)

            await session.commit()

            # Re-query to eagerly load settings after commit
            q2 = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(UserModel.id == user_id)
            )
            result2 = await session.execute(q2)
            return user_from_orm(result2.scalar_one())

    async def update_settings(self, user_id: UUID, data: dict) -> User:
        async with self._session_factory() as session:
            q = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(UserModel.id == user_id, UserModel.deleted_at.is_(None))
            )
            result = await session.execute(q)
            row = result.scalar_one_or_none()
            if row is None:
                raise NotFoundError(f"User {user_id} not found")

            settings = row.settings
            if settings is None:
                settings = UserSettingsORM(user_id=user_id)
                session.add(settings)

            for key, value in data.items():
                if hasattr(settings, key) and key not in ("id", "user_id"):
                    setattr(settings, key, value)

            await session.commit()

            # Re-query to eagerly load settings after commit
            q2 = (
                select(UserModel)
                .options(selectinload(UserModel.settings))
                .where(UserModel.id == user_id)
            )
            result2 = await session.execute(q2)
            return user_from_orm(result2.scalar_one())

    async def soft_delete_user(self, user_id: UUID) -> None:
        async with self._session_factory() as session:
            q = select(UserModel).where(
                UserModel.id == user_id, UserModel.deleted_at.is_(None)
            )
            result = await session.execute(q)
            row = result.scalar_one_or_none()
            if row is None:
                raise NotFoundError(f"User {user_id} not found")

            row.deleted_at = func.now()
            await session.commit()
