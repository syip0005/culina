"""Unit tests for JWT verification — no DB required."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from culina_backend.auth.jwt import SupabaseClaims, extract_claims, verify_token
from culina_backend.service.errors import AuthenticationError

# ---------------------------------------------------------------------------
# EC keypair generated once per module (ES256 = P-256 curve)
# ---------------------------------------------------------------------------
_private_key = ec.generate_private_key(ec.SECP256R1())
_public_key = _private_key.public_key()

TEST_ISSUER = "https://test.supabase.co/auth/v1"
TEST_AUDIENCE = "authenticated"


def _encode_token(payload: dict) -> str:
    """Encode a JWT with the test RSA private key."""
    return pyjwt.encode(payload, _private_key, algorithm="ES256")


def _valid_payload(**overrides) -> dict:
    now = int(time.time())
    defaults = {
        "sub": "user-abc-123",
        "email": "test@example.com",
        "iss": TEST_ISSUER,
        "aud": TEST_AUDIENCE,
        "exp": now + 3600,
        "iat": now,
        "user_metadata": {"full_name": "Test User"},
    }
    defaults.update(overrides)
    return defaults


def _mock_jwks_client():
    """Return a mock PyJWKClient whose signing key uses our test public key."""
    mock_client = MagicMock()
    mock_signing_key = MagicMock()
    mock_signing_key.key = _public_key
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    return mock_client


# ---------------------------------------------------------------------------
# verify_token tests
# ---------------------------------------------------------------------------


class TestVerifyToken:
    def test_valid_token(self):
        token = _encode_token(_valid_payload())
        mock_client = _mock_jwks_client()

        with (
            patch("culina_backend.auth.jwt.jwks_client", mock_client),
            patch("culina_backend.auth.jwt.secrets") as mock_secrets,
        ):
            mock_secrets.SUPABASE_JWT_ISSUER = TEST_ISSUER
            payload = verify_token(token)

        assert payload["sub"] == "user-abc-123"
        assert payload["email"] == "test@example.com"

    def test_expired_token(self):
        token = _encode_token(_valid_payload(exp=int(time.time()) - 100))
        mock_client = _mock_jwks_client()

        with (
            patch("culina_backend.auth.jwt.jwks_client", mock_client),
            patch("culina_backend.auth.jwt.secrets") as mock_secrets,
        ):
            mock_secrets.SUPABASE_JWT_ISSUER = TEST_ISSUER
            with pytest.raises(AuthenticationError):
                verify_token(token)

    def test_wrong_issuer(self):
        token = _encode_token(_valid_payload(iss="https://evil.example.com"))
        mock_client = _mock_jwks_client()

        with (
            patch("culina_backend.auth.jwt.jwks_client", mock_client),
            patch("culina_backend.auth.jwt.secrets") as mock_secrets,
        ):
            mock_secrets.SUPABASE_JWT_ISSUER = TEST_ISSUER
            with pytest.raises(AuthenticationError):
                verify_token(token)

    def test_wrong_audience(self):
        token = _encode_token(_valid_payload(aud="wrong-audience"))
        mock_client = _mock_jwks_client()

        with (
            patch("culina_backend.auth.jwt.jwks_client", mock_client),
            patch("culina_backend.auth.jwt.secrets") as mock_secrets,
        ):
            mock_secrets.SUPABASE_JWT_ISSUER = TEST_ISSUER
            with pytest.raises(AuthenticationError):
                verify_token(token)

    def test_malformed_token(self):
        mock_client = _mock_jwks_client()
        mock_client.get_signing_key_from_jwt.side_effect = pyjwt.PyJWTError(
            "Invalid token"
        )

        with (
            patch("culina_backend.auth.jwt.jwks_client", mock_client),
            patch("culina_backend.auth.jwt.secrets") as mock_secrets,
        ):
            mock_secrets.SUPABASE_JWT_ISSUER = TEST_ISSUER
            with pytest.raises(AuthenticationError):
                verify_token("not.a.jwt")


# ---------------------------------------------------------------------------
# extract_claims tests
# ---------------------------------------------------------------------------


class TestExtractClaims:
    def test_google_metadata(self):
        payload = _valid_payload(
            user_metadata={
                "full_name": "Google User",
                "avatar_url": "https://example.com/photo.jpg",
            },
        )
        claims = extract_claims(payload)

        assert claims.sub == "user-abc-123"
        assert claims.email == "test@example.com"
        assert claims.display_name == "Google User"

    def test_name_fallback_order(self):
        # Falls back to "name" when "full_name" is absent
        claims = extract_claims(_valid_payload(user_metadata={"name": "Name Only"}))
        assert claims.display_name == "Name Only"

        # Falls back to "display_name" when both are absent
        claims = extract_claims(
            _valid_payload(user_metadata={"display_name": "Display Only"})
        )
        assert claims.display_name == "Display Only"

    def test_minimal_payload(self):
        payload = {"sub": "minimal-user"}
        claims = extract_claims(payload)

        assert claims.sub == "minimal-user"
        assert claims.email is None
        assert claims.display_name is None
        assert claims.user_metadata == {}


# ---------------------------------------------------------------------------
# SupabaseClaims model tests
# ---------------------------------------------------------------------------


class TestSupabaseClaims:
    def test_display_name_empty_metadata(self):
        claims = SupabaseClaims(sub="x")
        assert claims.display_name is None

    def test_display_name_prefers_full_name(self):
        claims = SupabaseClaims(
            sub="x",
            user_metadata={
                "full_name": "Full",
                "name": "Name",
                "display_name": "Display",
            },
        )
        assert claims.display_name == "Full"
