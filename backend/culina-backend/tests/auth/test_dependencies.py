"""Integration tests for auth dependencies — uses DB fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from culina_backend.auth.dependencies import get_current_user
from culina_backend.model.user import User
from culina_backend.service.user import UserService

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_credentials(token: str = "valid-token") -> MagicMock:
    creds = MagicMock()
    creds.credentials = token
    return creds


def _patch_verify(payload: dict):
    """Patch verify_token and extract_claims to return known data."""
    return patch(
        "culina_backend.auth.dependencies.verify_token",
        return_value=payload,
    )


def _valid_payload(**overrides) -> dict:
    defaults = {
        "sub": "supabase-uid-001",
        "email": "new@example.com",
        "user_metadata": {"full_name": "New User"},
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAutoProvision:
    async def test_new_user_is_created(self, user_service: UserService):
        payload = _valid_payload()

        with _patch_verify(payload):
            user = await get_current_user(_make_credentials(), user_service)

        assert user.external_id == "supabase-uid-001"
        assert user.email == "new@example.com"
        assert user.display_name == "New User"

        # Verify persisted in DB
        fetched = await user_service.get_user_by_external_id("supabase-uid-001")
        assert fetched is not None
        assert fetched.id == user.id

    async def test_existing_user_is_returned(self, user_service: UserService):
        # Pre-create the user
        existing = await user_service.create_user(
            User(
                external_id="supabase-uid-002",
                email="existing@example.com",
                display_name="Existing",
            )
        )

        payload = _valid_payload(
            sub="supabase-uid-002",
            email="existing@example.com",
            user_metadata={"full_name": "Existing"},
        )

        with _patch_verify(payload):
            user = await get_current_user(_make_credentials(), user_service)

        assert user.id == existing.id
        assert user.external_id == "supabase-uid-002"


class TestProfileSync:
    async def test_sync_email_on_change(self, user_service: UserService):
        await user_service.create_user(
            User(
                external_id="sync-uid-001",
                email="old@example.com",
                display_name="User",
            )
        )

        payload = _valid_payload(
            sub="sync-uid-001",
            email="updated@example.com",
            user_metadata={"full_name": "User"},
        )

        with _patch_verify(payload):
            user = await get_current_user(_make_credentials(), user_service)

        assert user.email == "updated@example.com"

    async def test_sync_display_name_on_change(self, user_service: UserService):
        await user_service.create_user(
            User(
                external_id="sync-uid-002",
                email="user@example.com",
                display_name="Old Name",
            )
        )

        payload = _valid_payload(
            sub="sync-uid-002",
            email="user@example.com",
            user_metadata={"full_name": "New Name"},
        )

        with _patch_verify(payload):
            user = await get_current_user(_make_credentials(), user_service)

        assert user.display_name == "New Name"


class TestDuplicateRaceCondition:
    async def test_duplicate_error_refetches(self, user_service: UserService):
        """Simulate race: create_user raises DuplicateError, then re-fetch succeeds."""
        from culina_backend.service.errors import DuplicateError

        payload = _valid_payload(sub="race-uid-001")

        # The race condition user that "another request" created
        race_user = User(
            external_id="race-uid-001",
            email="race@example.com",
            display_name="Racer",
        )
        created = await user_service.create_user(race_user)

        # Mock create_user to raise DuplicateError (simulating the race),
        # while get_user_by_external_id returns None first, then the real user
        original_get = user_service.get_user_by_external_id
        get_call_count = 0

        async def _mock_get(external_id: str):
            nonlocal get_call_count
            get_call_count += 1
            if get_call_count == 1:
                return None  # First lookup misses (race window)
            return await original_get(external_id)  # Re-fetch finds it

        async def _mock_create(data: User):
            raise DuplicateError("duplicate external_id")

        with (
            _patch_verify(payload),
            patch.object(
                user_service, "get_user_by_external_id", side_effect=_mock_get
            ),
            patch.object(user_service, "create_user", side_effect=_mock_create),
        ):
            user = await get_current_user(_make_credentials(), user_service)

        assert user.external_id == "race-uid-001"
        assert user.id == created.id


class TestInvalidToken:
    async def test_invalid_token_returns_401(self, user_service: UserService):
        from culina_backend.service.errors import AuthenticationError

        with patch(
            "culina_backend.auth.dependencies.verify_token",
            side_effect=AuthenticationError("Token expired"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(_make_credentials("bad-token"), user_service)

        assert exc_info.value.status_code == 401
        assert "Token expired" in exc_info.value.detail
