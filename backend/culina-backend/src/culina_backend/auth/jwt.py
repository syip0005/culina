"""JWT verification for Supabase Auth tokens."""

import jwt
from jwt import PyJWKClient
from loguru import logger

from pydantic import BaseModel

from culina_backend.config import secrets
from culina_backend.service.errors import AuthenticationError

jwks_client = PyJWKClient(secrets.SUPABASE_JWKS_URL)


class SupabaseClaims(BaseModel):
    """Claims extracted from a verified Supabase JWT."""

    sub: str
    email: str | None = None
    user_metadata: dict = {}

    @property
    def display_name(self) -> str | None:
        for key in ("full_name", "name", "display_name"):
            if value := self.user_metadata.get(key):
                return value
        return None


def verify_token(token: str) -> dict:
    """Decode and verify a Supabase JWT. Returns the raw payload dict."""
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            issuer=secrets.SUPABASE_JWT_ISSUER,
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        logger.warning("JWT verification failed: {}", str(exc))
        raise AuthenticationError(str(exc)) from exc
    return payload


def extract_claims(payload: dict) -> SupabaseClaims:
    """Extract typed claims from a raw JWT payload."""
    return SupabaseClaims(
        sub=payload["sub"],
        email=payload.get("email"),
        user_metadata=payload.get("user_metadata", {}),
    )
