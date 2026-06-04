from __future__ import annotations

import json
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
        self._redis: Redis | None = None
        if Redis is not None:
            try:
                client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.2)
                client.ping()
                self._redis = client
            except RedisError:
                self._redis = None

    def get_json(self, key: str) -> Any | None:
        raw: str | None
        if self._redis:
            try:
                raw = self._redis.get(key)
            except RedisError:
                raw = self._memory.get(key)
        else:
            raw = self._memory.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, value: Any, expire_seconds: int = 300) -> None:
        raw = json.dumps(value, ensure_ascii=False)
        self._memory[key] = raw
        if self._redis:
            try:
                self._redis.setex(key, expire_seconds, raw)
            except RedisError:
                return

    def delete(self, key: str) -> None:
        self._memory.pop(key, None)
        if self._redis:
            try:
                self._redis.delete(key)
            except RedisError:
                return


cache_client = CacheClient()
