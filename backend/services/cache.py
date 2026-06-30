from __future__ import annotations

import hashlib
import json
import pickle
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Callable, Protocol, TypeVar


T = TypeVar("T")


class KeyValueCache(Protocol):
    """Interface de cache simple, reutilisable cote FastAPI."""

    def get(self, key: str) -> Any | None:  # noqa: D401
        ...

    def set(self, key: str, value: Any, *, ttl_s: float | None = None) -> None:
        ...


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def make_key(namespace: str, *parts: str) -> str:
    safe = ":".join(p.replace(":", "_") for p in parts)
    return f"{namespace}:{safe}"


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    size: int


class NullCache:
    """Cache no-op."""

    def get(self, key: str) -> Any | None:
        return None

    def set(self, key: str, value: Any, *, ttl_s: float | None = None) -> None:
        return


class InMemoryCache:
    """Cache en memoire thread-safe avec TTL optionnel."""

    def __init__(self, max_items: int = 256):
        self._max_items = int(max_items)
        self._lock = RLock()
        # key -> (expires_at_monotonic | None, value)
        self._data: OrderedDict[str, tuple[float | None, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        now = monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at is not None and now >= expires_at:
                self._data.pop(key, None)
                return None
            # Rafraichit l'ordre LRU
            self._data.pop(key, None)
            self._data[key] = (expires_at, value)
            return value

    def set(self, key: str, value: Any, *, ttl_s: float | None = None) -> None:
        expires_at = None
        if ttl_s is not None:
            expires_at = monotonic() + float(ttl_s)
        with self._lock:
            if key in self._data:
                self._data.pop(key)
            self._data[key] = (expires_at, value)
            while len(self._data) > self._max_items:
                self._data.popitem(last=False)


def make_cache_key(*, namespace: str, version: str, payload: Any) -> str:
    """Cree une cle de cache stable.

    payload doit etre JSON-dumpable (ou convertible via default=str).
    """

    blob = stable_json_dumps({"version": version, "payload": payload})
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return make_key(namespace, digest)
