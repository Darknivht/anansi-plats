"""
Anansi Security — Password hashing, JWT creation/verification, and rate limiting logic.

Uses bcrypt (cost 12) for passwords, RS256 JWT with 2048-bit RSA keys,
and a Redis-backed token-bucket rate limiter.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import jwt as jose_jwt
from jose.constants import Algorithms
from jose.exceptions import ExpiredSignatureError, JOSEError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from redis.asyncio import Redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


# ─── RSA Key Management ─────────────────────────────────────────────────────────


def _generate_rsa_keypair() -> tuple[bytes, bytes]:
    """Generate a 2048-bit RSA key pair for development use.

    Returns:
        Tuple of (private_key_pem, public_key_pem).
    """
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _load_keys() -> tuple[bytes, bytes]:
    """Load RSA keys from settings or generate development keys."""
    if settings.jwt.private_key:
        private_pem = settings.jwt.private_key.encode("utf-8")
        public_pem = (
            settings.jwt.public_key.encode("utf-8")
            if settings.jwt.public_key
            else private_pem
        )
        return private_pem, public_pem

    logger.warning("No JWT RSA keys configured — generating ephemeral keys (development mode)")
    return _generate_rsa_keypair()


_RSA_PRIVATE_KEY, _RSA_PUBLIC_KEY = _load_keys()


# ─── Password Hashing ────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with cost factor 12.

    Args:
        password: Plain-text password.

    Returns:
        bcrypt hash string.
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    rounds: int = max(4, min(31, settings.app.bcrypt_rounds))
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash.

    Args:
        plain_password: Plain-text password to check.
        hashed_password: Stored bcrypt hash.

    Returns:
        True if the password matches.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError) as exc:
        logger.error("Password verification failed", error=str(exc))
        return False


# ─── JWT Creation & Verification ─────────────────────────────────────────────────


def create_access_token(
    subject: str,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_in_minutes: int | None = None,
) -> str:
    """Create a short-lived JWT access token (RS256).

    Args:
        subject: The user ID (sub claim).
        extra_claims: Additional claims to embed in the token.
        expires_in_minutes: Token lifetime (default: 15 min from settings).

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire_minutes = expires_in_minutes or settings.jwt.access_token_expire_minutes
    payload: dict[str, Any] = {
        "sub": subject,
        "iss": settings.jwt.issuer,
        "aud": settings.jwt.audience,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jose_jwt.encode(
        payload,
        _RSA_PRIVATE_KEY,
        algorithm=settings.jwt.algorithm,
    )
    return token


def create_refresh_token(
    subject: str,
    *,
    extra_claims: dict[str, Any] | None = None,
    expires_in_days: int | None = None,
) -> str:
    """Create a long-lived JWT refresh token (RS256).

    Args:
        subject: The user ID (sub claim).
        extra_claims: Additional claims.
        expires_in_days: Token lifetime (default: 7 days from settings).

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire_days = expires_in_days or settings.jwt.refresh_token_expire_days
    payload: dict[str, Any] = {
        "sub": subject,
        "iss": settings.jwt.issuer,
        "aud": settings.jwt.audience,
        "iat": now,
        "exp": now + timedelta(days=expire_days),
        "type": "refresh",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jose_jwt.encode(
        payload,
        _RSA_PRIVATE_KEY,
        algorithm=settings.jwt.algorithm,
    )
    return token


def verify_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Verify a JWT and return its payload.

    Args:
        token: Encoded JWT string.
        expected_type: Expected token type ('access' or 'refresh').

    Returns:
        Decoded payload dictionary.

    Raises:
        ValueError: If the token is invalid, expired, or wrong type.
    """
    try:
        payload = jose_jwt.decode(
            token,
            _RSA_PUBLIC_KEY,
            algorithms=[settings.jwt.algorithm],
            audience=settings.jwt.audience,
            issuer=settings.jwt.issuer,
        )
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except JOSEError as exc:
        raise ValueError(f"Token verification failed: {exc}")

    token_type = payload.get("type")
    if token_type != expected_type:
        raise ValueError(
            f"Invalid token type: expected '{expected_type}', got '{token_type}'"
        )

    return payload


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT without verification (useful for debugging).

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded payload (not verified).
    """
    return jose_jwt.get_unverified_claims(token)


# ─── Rate Limiting (Token Bucket via Redis) ──────────────────────────────────────


class TokenBucketRateLimiter:
    """Redis-backed token bucket rate limiter.

    Each key gets a bucket that refills at ``rate / window`` tokens per second,
    with a maximum capacity of ``rate`` tokens.
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """Check if a request is within the rate limit.

        Args:
            key: Unique identifier (user ID, IP, etc.).
            max_requests: Maximum number of requests allowed in the window.
            window_seconds: Time window in seconds.

        Returns:
            Tuple of (allowed, remaining, retry_after_seconds).
            ``allowed`` is True if the request should be permitted.
        """
        redis_key = f"rate_limit:{key}"
        now = time.time()
        bucket_key = f"{redis_key}:bucket"

        # Lua script for atomic token-bucket operation
        lua_script = """
        local bucket_key = KEYS[1]
        local max_tokens = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local rate = max_tokens / window
        local bucket = redis.call('HMGET', bucket_key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or max_tokens
        local last_refill = tonumber(bucket[2]) or now

        -- Refill tokens
        local elapsed = now - last_refill
        tokens = math.min(max_tokens, tokens + elapsed * rate)

        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', bucket_key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', bucket_key, math.ceil(window * 1.5))
            return {1, math.floor(tokens), 0}
        else
            local retry_after = math.ceil((1 - tokens) / rate)
            redis.call('EXPIRE', bucket_key, math.ceil(window * 1.5))
            return {0, 0, retry_after}
        end
        """

        try:
            result = await self.redis.eval(
                lua_script,
                keys=[bucket_key],
                args=[str(max_requests), str(window_seconds), str(now)],
            )
            allowed = bool(result[0])
            remaining = int(result[1])
            retry_after = int(result[2])
            return allowed, remaining, retry_after
        except Exception as exc:
            logger.error("Rate limiter error", key=key, error=str(exc))
            # On Redis failure, allow the request (fail open)
            return True, max_requests, 0

    async def get_remaining(self, key: str, max_requests: int) -> int:
        """Get remaining tokens without consuming one."""
        bucket_key = f"rate_limit:{key}:bucket"
        try:
            bucket = await self.redis.hmget(bucket_key, "tokens", "last_refill")
            if not bucket or bucket[0] is None:
                return max_requests
            tokens = float(bucket[0])
            last_refill = float(bucket[1] or time.time())
            elapsed = time.time() - last_refill
            rate = max_requests / 60  # default window
            refilled = min(max_requests, tokens + elapsed * rate)
            return max(0, int(refilled))
        except Exception:
            return max_requests


# ─── Singleton ───────────────────────────────────────────────────────────────────

_rate_limiter_instance: TokenBucketRateLimiter | None = None


def get_rate_limiter(redis: Redis | None = None) -> TokenBucketRateLimiter:
    """Get or create the singleton rate limiter.

    Args:
        redis: Redis client instance (required on first call).

    Returns:
        TokenBucketRateLimiter instance.
    """
    global _rate_limiter_instance
    if _rate_limiter_instance is None and redis is not None:
        _rate_limiter_instance = TokenBucketRateLimiter(redis)
    elif _rate_limiter_instance is None:
        raise RuntimeError("Rate limiter not initialised — provide a Redis client")
    return _rate_limiter_instance


def init_rate_limiter(redis: Redis) -> None:
    """Initialise the rate limiter singleton.

    Called during app startup.
    """
    global _rate_limiter_instance
    _rate_limiter_instance = TokenBucketRateLimiter(redis)
    logger.info("Rate limiter initialised")


def get_public_key_pem() -> str:
    """Return the RSA public key in PEM format (for JWKS endpoint)."""
    return _RSA_PUBLIC_KEY.decode("utf-8")


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "TokenBucketRateLimiter",
    "get_rate_limiter",
    "init_rate_limiter",
    "get_public_key_pem",
]
