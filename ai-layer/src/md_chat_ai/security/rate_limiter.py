"""Namespaced rate limiter — Redis backend with in-memory fallback.

Ported from Cronberry's rate_limiter.py and reshaped to MD-Chat's needs:
- Per-endpoint *namespaces* instead of global+endpoint stacking. Each call
  picks a namespace ("signup", "twin-chat", "briefing", ...) and is limited
  independently against the configured cooldown / quota.
- Pluggable backend: if `redis` is reachable, counters live in Redis so
  multiple ai-layer replicas share state. Otherwise we fall back to an
  in-process token-bucket store identical in behaviour to Cronberry's.
- Pure API, no Flask coupling: returns `RateLimitResult(allowed, retry_after)`
  so digital_twin and api endpoints can decide how to respond.

Cooldowns (per requirements):
    signup    → 60 seconds  (1 attempt per minute per identifier)
    twin-chat →  2 seconds  (30 / minute)
    briefing  → 60 minutes  (1 / hour)

Any other namespace defaults to 100 / 60 s. Override via `set_namespace()`.

License: Apache 2.0 (Mega Promoting SRL, derived from cronberry_swarm).
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ..config import CONFIG  # noqa: F401  -- imported for future config hooks

logger = logging.getLogger("md_chat_ai.security.rate_limiter")


# ---------------------------------------------------------------------------
# Namespace configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NamespaceLimit:
    """One namespace's quota.

    `capacity` = max calls in `window_seconds`.
    For pure cooldown semantics (one call per N s) use capacity=1 and
    window_seconds=cooldown.
    """

    capacity: int
    window_seconds: float

    @property
    def refill_rate(self) -> float:
        """Tokens added per second for the in-memory token bucket backend."""
        return self.capacity / self.window_seconds if self.window_seconds > 0 else 1e9


_DEFAULT_NAMESPACES: Dict[str, NamespaceLimit] = {
    # 1 signup attempt every 60 s per IP / phone — anti-flood.
    "signup":    NamespaceLimit(capacity=1,  window_seconds=60.0),
    # ~30 messages per minute per user.
    "twin-chat": NamespaceLimit(capacity=30, window_seconds=60.0),
    # 1 morning / evening briefing per hour per user.
    "briefing":  NamespaceLimit(capacity=1,  window_seconds=3600.0),
    # Fallback for any namespace that isn't explicitly configured.
    "default":   NamespaceLimit(capacity=100, window_seconds=60.0),
}


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a single allowance check."""

    allowed: bool
    retry_after: float  # seconds the caller should wait before trying again
    namespace: str
    identifier: str

    def as_dict(self) -> Dict[str, object]:
        return {
            "allowed": self.allowed,
            "retry_after": int(self.retry_after) + (0 if self.allowed else 1),
            "namespace": self.namespace,
            "identifier": self.identifier,
        }


# ---------------------------------------------------------------------------
# In-memory token bucket backend
# ---------------------------------------------------------------------------

class _TokenBucket:
    """Single thread-safe token bucket used by the in-memory backend."""

    __slots__ = ("capacity", "rate", "tokens", "last_refill", "lock")

    def __init__(self, capacity: int, rate: float) -> None:
        self.capacity: float = float(capacity)
        self.rate: float = rate
        self.tokens: float = float(capacity)
        self.last_refill: float = time.monotonic()
        self.lock: threading.Lock = threading.Lock()

    def consume(self) -> Tuple[bool, float]:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.last_refill = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True, 0.0
            retry_after = (1.0 - self.tokens) / self.rate if self.rate > 0 else 60.0
            return False, retry_after


class _InMemoryBackend:
    """Fallback backend when Redis is unavailable. Process-local only."""

    _EVICT_AFTER_SECONDS: float = 3600.0
    _EVICT_CHECK_INTERVAL: float = 300.0

    def __init__(self) -> None:
        self._buckets: Dict[Tuple[str, str], _TokenBucket] = {}
        self._last_access: Dict[Tuple[str, str], float] = {}
        self._lock = threading.Lock()
        self._last_eviction = time.monotonic()

    def consume(
        self, namespace: str, identifier: str, limit: NamespaceLimit
    ) -> Tuple[bool, float]:
        key = (namespace, identifier)
        with self._lock:
            self._maybe_evict()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _TokenBucket(limit.capacity, limit.refill_rate)
                self._buckets[key] = bucket
            self._last_access[key] = time.monotonic()
        return bucket.consume()

    def reset(self, namespace: Optional[str] = None) -> None:
        with self._lock:
            if namespace is None:
                self._buckets.clear()
                self._last_access.clear()
            else:
                stale = [k for k in self._buckets if k[0] == namespace]
                for k in stale:
                    self._buckets.pop(k, None)
                    self._last_access.pop(k, None)

    def _maybe_evict(self) -> None:
        now = time.monotonic()
        if now - self._last_eviction < self._EVICT_CHECK_INTERVAL:
            return
        self._last_eviction = now
        cutoff = now - self._EVICT_AFTER_SECONDS
        stale = [k for k, t in self._last_access.items() if t < cutoff]
        for k in stale:
            self._buckets.pop(k, None)
            self._last_access.pop(k, None)


# ---------------------------------------------------------------------------
# Redis backend (lazy import, optional)
# ---------------------------------------------------------------------------

class _RedisBackend:
    """Fixed-window counter using `INCR` + `EXPIRE` in Redis.

    Atomic via a 2-call pipeline; sufficient for our throughput requirements
    and avoids the complexity of running a Lua token-bucket script.
    """

    def __init__(self, client) -> None:  # type: ignore[no-untyped-def]
        self._r = client

    def consume(
        self, namespace: str, identifier: str, limit: NamespaceLimit
    ) -> Tuple[bool, float]:
        # Fixed window keyed by `floor(now / window_seconds)` so that a fresh
        # window grants a clean quota without a sliding TTL.
        now = time.time()
        window_idx = int(now // limit.window_seconds)
        key = f"mdchat:rl:{namespace}:{identifier}:{window_idx}"
        try:
            pipe = self._r.pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, int(limit.window_seconds) + 1)
            count, _ = pipe.execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "RateLimiter: Redis error namespace=%s id=%s: %s — failing open",
                namespace, identifier, exc,
            )
            return True, 0.0

        if count <= limit.capacity:
            return True, 0.0
        # Seconds until the current window closes.
        retry_after = ((window_idx + 1) * limit.window_seconds) - now
        return False, max(1.0, retry_after)

    def reset(self, namespace: Optional[str] = None) -> None:
        pattern = f"mdchat:rl:{namespace or '*'}:*"
        try:
            for key in self._r.scan_iter(match=pattern, count=500):
                self._r.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RateLimiter: Redis reset failed: %s", exc)


# ---------------------------------------------------------------------------
# Public façade
# ---------------------------------------------------------------------------

class RateLimiter:
    """Namespaced rate limiter with pluggable backend.

    Construct with no arguments to use the default backend selection logic
    (Redis if `REDIS_URL` is set and reachable, else in-memory). Pass
    `backend="memory"` explicitly to skip the Redis probe (useful in tests).
    """

    def __init__(
        self,
        backend: Optional[str] = None,
        redis_url: Optional[str] = None,
        namespaces: Optional[Dict[str, NamespaceLimit]] = None,
    ) -> None:
        self._namespaces: Dict[str, NamespaceLimit] = dict(_DEFAULT_NAMESPACES)
        if namespaces:
            self._namespaces.update(namespaces)

        if backend == "memory":
            self._backend = _InMemoryBackend()
            self._backend_name = "memory"
            return

        # Try Redis when available and not explicitly forced to memory.
        client = self._try_redis(redis_url) if backend in (None, "redis") else None
        if client is not None:
            self._backend = _RedisBackend(client)
            self._backend_name = "redis"
            logger.info("RateLimiter: using Redis backend")
        else:
            self._backend = _InMemoryBackend()
            self._backend_name = "memory"
            logger.info("RateLimiter: using in-memory backend (no Redis)")

    @staticmethod
    def _try_redis(redis_url: Optional[str]):  # type: ignore[no-untyped-def]
        import os
        url = redis_url or os.environ.get("REDIS_URL")
        if not url:
            return None
        try:
            import redis  # type: ignore[import-not-found]
            client = redis.Redis.from_url(url, socket_connect_timeout=1, decode_responses=True)
            client.ping()
            return client
        except Exception as exc:  # noqa: BLE001
            logger.warning("RateLimiter: Redis unavailable (%s) — falling back to memory", exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def set_namespace(self, namespace: str, limit: NamespaceLimit) -> None:
        """Override the limit for a namespace at runtime (tests, hot-config)."""
        self._namespaces[namespace] = limit

    def check(self, namespace: str, identifier: str) -> RateLimitResult:
        """Try to consume one slot for (namespace, identifier).

        `identifier` should be a stable per-user key (matrix ID, phone, IP).
        """
        limit = self._namespaces.get(namespace) or self._namespaces["default"]
        allowed, retry_after = self._backend.consume(namespace, identifier, limit)
        if not allowed:
            logger.info(
                "RateLimiter: 429 namespace=%s id=%s retry_after=%.1fs",
                namespace, identifier, retry_after,
            )
        return RateLimitResult(
            allowed=allowed,
            retry_after=retry_after,
            namespace=namespace,
            identifier=identifier,
        )

    def reset(self, namespace: Optional[str] = None) -> None:
        """Clear all counters (optionally only for one namespace). Test-only."""
        self._backend.reset(namespace)


# Module-level singleton.
_limiter: Optional[RateLimiter] = None


def get_limiter() -> RateLimiter:
    """Return (or lazily create) the module-level RateLimiter singleton."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_limiter() -> None:
    """Drop the singleton — used by tests to swap backends."""
    global _limiter
    _limiter = None
