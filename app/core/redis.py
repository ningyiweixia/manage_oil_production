from __future__ import annotations

import json
import time
from typing import Any

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # Redis is optional in local dev; production installs requirements.txt.
    Redis = None  # type: ignore[assignment]

    class RedisError(Exception):
        pass

from app.core.config import settings


class CacheClient:
    def __init__(self) -> None:
        self._memory: dict[str, str] = {}
        self._memory_expire_at: dict[str, float] = {}
        self._redis: Redis | None = None
        if Redis is not None and settings.redis_url:
            try:
                client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.2)
                client.ping()
                self._redis = client
            except RedisError:
                self._redis = None

    def _memory_get(self, key: str) -> str | None:
        expire_at = self._memory_expire_at.get(key)
        if expire_at is not None and expire_at <= time.monotonic():
            self._memory.pop(key, None)
            self._memory_expire_at.pop(key, None)
            return None
        return self._memory.get(key)

    @property
    def distributed_lock_available(self) -> bool:
        """Memory cache is acceptable only when Redis was not configured (local dev)."""
        return not settings.redis_url or self._redis is not None

    def _memory_set_nx(self, key: str, raw: str, expire_seconds: int) -> bool:
        if self._memory_get(key) is not None:
            return False
        self._memory[key] = raw
        self._memory_expire_at[key] = time.monotonic() + expire_seconds
        return True

    def get_json(self, key: str) -> Any | None:
        raw: str | None
        if self._redis:
            try:
                raw = self._redis.get(key)
            except RedisError:
                raw = self._memory_get(key)
        else:
            raw = self._memory_get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, value: Any, expire_seconds: int = 300, *, nx: bool = False) -> bool:
        raw = json.dumps(value, ensure_ascii=False)
        if self._redis:
            try:
                result = self._redis.set(key, raw, ex=expire_seconds, nx=nx)
                return bool(result)
            except RedisError:
                pass
        if nx:
            return self._memory_set_nx(key, raw, expire_seconds)
        self._memory[key] = raw
        self._memory_expire_at[key] = time.monotonic() + expire_seconds
        return True

    def set_lock_json(self, key: str, value: Any, expire_seconds: int, *, nx: bool = True) -> bool:
        """Set a critical lock without falling back to per-process memory after Redis failure."""
        raw = json.dumps(value, ensure_ascii=False)
        if settings.redis_url:
            if self._redis is None:
                return False
            try:
                return bool(self._redis.set(key, raw, ex=expire_seconds, nx=nx))
            except RedisError:
                self._redis = None
                return False
        return self._memory_set_nx(key, raw, expire_seconds) if nx else self.set_json(key, value, expire_seconds)

    def delete(self, key: str) -> None:
        self._memory.pop(key, None)
        self._memory_expire_at.pop(key, None)
        if self._redis:
            try:
                self._redis.delete(key)
            except RedisError:
                return

    def delete_json_if_matches(self, key: str, value: Any) -> bool:
        """Delete a JSON key only when it still belongs to this caller."""
        raw = json.dumps(value, ensure_ascii=False)
        if self._redis:
            try:
                return bool(self._redis.eval(
                    "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end",
                    1, key, raw,
                ))
            except RedisError:
                pass
        if self._memory_get(key) != raw:
            return False
        self._memory.pop(key, None)
        self._memory_expire_at.pop(key, None)
        return True


cache_client = CacheClient()
