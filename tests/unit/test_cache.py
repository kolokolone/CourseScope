from __future__ import annotations

import unittest

from tests.unit._bootstrap import ensure_project_on_path


ensure_project_on_path()


class TestCache(unittest.TestCase):
    def test_inmemory_cache_set_get(self) -> None:
        from services.cache import InMemoryCache

        c = InMemoryCache(max_items=2)
        c.set("a", 1)
        self.assertEqual(c.get("a"), 1)
        self.assertIsNone(c.get("missing"))

    def test_make_cache_key_is_stable(self) -> None:
        from services.cache import make_cache_key

        k1 = make_cache_key(namespace="x", version="v1", payload={"a": 1, "b": 2})
        k2 = make_cache_key(namespace="x", version="v1", payload={"b": 2, "a": 1})
        self.assertEqual(k1, k2)

    def test_inmemory_cache_ttl_expires(self) -> None:
        from services.cache import InMemoryCache

        c = InMemoryCache(max_items=2)
        c.set("a", 1, ttl_s=0)
        self.assertIsNone(c.get("a"))


if __name__ == "__main__":
    unittest.main()
