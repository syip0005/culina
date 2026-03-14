"""Tests for UserService."""

from __future__ import annotations

from uuid import uuid4

import pytest

from culina_backend.model.user import User, UserFilter
from culina_backend.service.errors import DuplicateError, NotFoundError
from culina_backend.service.user import UserService

pytestmark = pytest.mark.asyncio


# ---- helpers ---------------------------------------------------------------


def _make_user(**overrides) -> User:
    defaults = dict(
        external_id=f"ext-{uuid4().hex[:8]}",
        email="test@example.com",
        display_name="Test User",
    )
    defaults.update(overrides)
    return User(**defaults)


# ---- Create ----------------------------------------------------------------


class TestCreateUser:
    async def test_create_returns_user_with_default_settings(
        self, user_service: UserService
    ):
        data = _make_user(external_id="create-test", email="create@example.com")
        result = await user_service.create_user(data)

        assert result.external_id == "create-test"
        assert result.email == "create@example.com"
        assert result.settings is not None
        assert result.settings.timezone == "Australia/Sydney"
        assert result.settings.preferred_energy_unit == "kj"

    async def test_create_duplicate_external_id_raises(self, user_service: UserService):
        data = _make_user(external_id="dup-ext")
        await user_service.create_user(data)

        data2 = _make_user(external_id="dup-ext", email="other@example.com")
        with pytest.raises(DuplicateError):
            await user_service.create_user(data2)


# ---- Get -------------------------------------------------------------------


class TestGetUser:
    async def test_get_by_id(self, user_service: UserService):
        created = await user_service.create_user(
            _make_user(external_id="get-id", email="getid@example.com")
        )
        result = await user_service.get_user(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.settings is not None

    async def test_get_by_email(self, user_service: UserService):
        await user_service.create_user(
            _make_user(external_id="get-email", email="byemail@example.com")
        )
        result = await user_service.get_user_by_email("byemail@example.com")

        assert result is not None
        assert result.email == "byemail@example.com"

    async def test_get_by_external_id(self, user_service: UserService):
        await user_service.create_user(
            _make_user(external_id="get-ext-id", email="ext@example.com")
        )
        result = await user_service.get_user_by_external_id("get-ext-id")

        assert result is not None
        assert result.external_id == "get-ext-id"

    async def test_get_nonexistent_returns_none(self, user_service: UserService):
        result = await user_service.get_user(uuid4())
        assert result is None

    async def test_get_deleted_returns_none(self, user_service: UserService):
        created = await user_service.create_user(
            _make_user(external_id="del-get", email="delget@example.com")
        )
        await user_service.soft_delete_user(created.id)

        assert await user_service.get_user(created.id) is None
        assert await user_service.get_user_by_email("delget@example.com") is None
        assert await user_service.get_user_by_external_id("del-get") is None


# ---- Exists ----------------------------------------------------------------


class TestUserExists:
    async def test_exists_true(self, user_service: UserService):
        created = await user_service.create_user(_make_user(external_id="exists-true"))
        assert await user_service.user_exists(created.id) is True

    async def test_exists_false(self, user_service: UserService):
        assert await user_service.user_exists(uuid4()) is False

    async def test_exists_false_for_deleted(self, user_service: UserService):
        created = await user_service.create_user(_make_user(external_id="exists-del"))
        await user_service.soft_delete_user(created.id)
        assert await user_service.user_exists(created.id) is False


# ---- List ------------------------------------------------------------------


class TestListUsers:
    async def test_list_all_active(self, user_service: UserService):
        await user_service.create_user(_make_user(external_id="list-a"))
        await user_service.create_user(_make_user(external_id="list-b"))

        results = await user_service.list_users()
        ext_ids = [u.external_id for u in results]
        assert "list-a" in ext_ids
        assert "list-b" in ext_ids

    async def test_filter_by_email(self, user_service: UserService):
        await user_service.create_user(
            _make_user(external_id="filter-e1", email="alice@testing.com")
        )
        await user_service.create_user(
            _make_user(external_id="filter-e2", email="bob@other.com")
        )

        results = await user_service.list_users(UserFilter(email="alice"))
        assert len(results) == 1
        assert results[0].email == "alice@testing.com"

    async def test_filter_by_display_name(self, user_service: UserService):
        await user_service.create_user(
            _make_user(
                external_id="filter-d1",
                display_name="Charlie Brown",
                email="c1@example.com",
            )
        )
        await user_service.create_user(
            _make_user(
                external_id="filter-d2",
                display_name="Diana Prince",
                email="c2@example.com",
            )
        )

        results = await user_service.list_users(UserFilter(display_name="charlie"))
        assert len(results) == 1
        assert results[0].display_name == "Charlie Brown"

    async def test_pagination(self, user_service: UserService):
        for i in range(5):
            await user_service.create_user(
                _make_user(external_id=f"page-{i}", email=f"page{i}@example.com")
            )

        page1 = await user_service.list_users(offset=0, limit=2)
        page2 = await user_service.list_users(offset=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    async def test_include_deleted(self, user_service: UserService):
        created = await user_service.create_user(
            _make_user(external_id="incl-del", email="incldel@example.com")
        )
        await user_service.soft_delete_user(created.id)

        without = await user_service.list_users()
        with_deleted = await user_service.list_users(UserFilter(include_deleted=True))

        without_ids = [u.id for u in without]
        with_ids = [u.id for u in with_deleted]

        assert created.id not in without_ids
        assert created.id in with_ids


# ---- Update ----------------------------------------------------------------


class TestUpdateUser:
    async def test_update_email_and_display_name(self, user_service: UserService):
        created = await user_service.create_user(
            _make_user(
                external_id="upd-u",
                email="old@example.com",
                display_name="Old Name",
            )
        )
        result = await user_service.update_user(
            created.id, {"email": "new@example.com", "display_name": "New Name"}
        )

        assert result.email == "new@example.com"
        assert result.display_name == "New Name"

    async def test_update_deleted_raises(self, user_service: UserService):
        created = await user_service.create_user(_make_user(external_id="upd-del"))
        await user_service.soft_delete_user(created.id)

        with pytest.raises(NotFoundError):
            await user_service.update_user(created.id, {"display_name": "Nope"})


# ---- UpdateSettings --------------------------------------------------------


class TestUpdateSettings:
    async def test_update_targets_and_timezone(self, user_service: UserService):
        created = await user_service.create_user(_make_user(external_id="upd-s"))
        result = await user_service.update_settings(
            created.id,
            {
                "daily_energy_target_kj": 8700.0,
                "timezone": "America/New_York",
            },
        )

        assert result.settings is not None
        assert result.settings.daily_energy_target_kj == 8700.0
        assert result.settings.timezone == "America/New_York"

    async def test_update_settings_missing_user_raises(self, user_service: UserService):
        with pytest.raises(NotFoundError):
            await user_service.update_settings(uuid4(), {"timezone": "UTC"})


# ---- SoftDelete ------------------------------------------------------------


class TestSoftDeleteUser:
    async def test_soft_delete(self, user_service: UserService):
        created = await user_service.create_user(_make_user(external_id="soft-del"))
        await user_service.soft_delete_user(created.id)

        # Not visible via normal get
        assert await user_service.get_user(created.id) is None

    async def test_soft_delete_visible_with_include_deleted(
        self, user_service: UserService
    ):
        created = await user_service.create_user(
            _make_user(external_id="soft-del-vis", email="softdel@example.com")
        )
        await user_service.soft_delete_user(created.id)

        results = await user_service.list_users(UserFilter(include_deleted=True))
        ids = [u.id for u in results]
        assert created.id in ids

    async def test_soft_delete_excluded_from_list(self, user_service: UserService):
        created = await user_service.create_user(
            _make_user(external_id="soft-del-list", email="softdellist@example.com")
        )
        await user_service.soft_delete_user(created.id)

        results = await user_service.list_users()
        ids = [u.id for u in results]
        assert created.id not in ids

    async def test_soft_delete_nonexistent_raises(self, user_service: UserService):
        with pytest.raises(NotFoundError):
            await user_service.soft_delete_user(uuid4())

    async def test_soft_delete_already_deleted_raises(self, user_service: UserService):
        created = await user_service.create_user(
            _make_user(external_id="soft-del-twice")
        )
        await user_service.soft_delete_user(created.id)

        with pytest.raises(NotFoundError):
            await user_service.soft_delete_user(created.id)
