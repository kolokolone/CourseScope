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


class MemoryCache:
    """Petit cache LRU reutilisable cote API (sans Streamlit)."""

    def __init__(self, max_items: int = 32):
        self._max_items = int(max_items)
        self._lock = RLock()
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(hits=self._hits, misses=self._misses, size=len(self._data))

    def get(self, key: str) -> Any:
        with self._lock:
            if key not in self._data:
                self._misses += 1
                raise KeyError(key)
            self._hits += 1
            value = self._data.pop(key)
            self._data[key] = value
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._data:
                self._data.pop(key)
            self._data[key] = value
            while len(self._data) > self._max_items:
                self._data.popitem(last=False)

    def get_or_set(self, key: str, factory: Callable[[], T]) -> T:
        try:
            return self.get(key)
        except KeyError:
            value = factory()
            self.set(key, value)
            return value


class DiskCache:
    """Cache optionnel base sur pickle (a garder desactive sauf besoin)."""

    def __init__(self, directory: str | Path):
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, key: str) -> Path:
        safe = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._dir / f"{safe}.pkl"

    def get(self, key: str) -> Any:
        path = self._path(key)
        with self._lock:
            if not path.exists():
                raise KeyError(key)
            with path.open("rb") as f:
                return pickle.load(f)

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        with self._lock:
            with path.open("wb") as f:
                pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)


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
