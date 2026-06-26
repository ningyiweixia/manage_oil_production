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

    def delete(self, key: str) -> None:
        self._memory.pop(key, None)
        self._memory_expire_at.pop(key, None)
        if self._redis:
            try:
                self._redis.delete(key)
            except RedisError:
                return


cache_client = CacheClient()
