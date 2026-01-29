"""
Caching Layer for API Responses

Caches API responses by image hash to avoid re-analyzing identical regions.
Supports in-memory, file-based, and SQLite backends.
"""
import hashlib
import json
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import threading


@dataclass
class CacheEntry:
    """A cached API response"""
    key: str
    value: str  # JSON-serialized
    created_at: float
    expires_at: Optional[float] = None
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class CacheBackend(ABC):
    """Abstract cache backend"""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a value by key"""
        pass

    @abstractmethod
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set a value with optional TTL in seconds"""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a key"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries"""
        pass

    @abstractmethod
    def stats(self) -> dict:
        """Get cache statistics"""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache backend"""

    def __init__(self, max_size: int = 1000):
        self._cache: dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None

            entry.hit_count += 1
            self._hits += 1
            return entry.value

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        with self._lock:
            # Evict if at max size
            if len(self._cache) >= self._max_size:
                self._evict_lru()

            expires_at = time.time() + ttl if ttl else None
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
            )

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "backend": "memory",
                "entries": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0,
            }

    def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._cache:
            return

        # Find entry with lowest hit count
        min_entry = min(self._cache.values(), key=lambda e: e.hit_count)
        del self._cache[min_entry.key]


class FileCache(CacheBackend):
    """File-based cache backend"""

    def __init__(self, cache_dir: Path):
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._meta_file = self._cache_dir / "_meta.json"
        self._lock = threading.Lock()
        self._load_meta()

    def _load_meta(self) -> None:
        if self._meta_file.exists():
            with open(self._meta_file) as f:
                self._meta = json.load(f)
        else:
            self._meta = {"hits": 0, "misses": 0, "entries": {}}

    def _save_meta(self) -> None:
        with open(self._meta_file, "w") as f:
            json.dump(self._meta, f)

    def _key_to_path(self, key: str) -> Path:
        # Use first 2 chars as subdirectory to avoid too many files in one dir
        subdir = key[:2] if len(key) >= 2 else "00"
        return self._cache_dir / subdir / f"{key}.json"

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            path = self._key_to_path(key)
            if not path.exists():
                self._meta["misses"] = self._meta.get("misses", 0) + 1
                return None

            try:
                with open(path) as f:
                    data = json.load(f)

                # Check expiration
                if data.get("expires_at") and time.time() > data["expires_at"]:
                    path.unlink()
                    self._meta["misses"] = self._meta.get("misses", 0) + 1
                    return None

                self._meta["hits"] = self._meta.get("hits", 0) + 1
                return data["value"]

            except (json.JSONDecodeError, KeyError):
                self._meta["misses"] = self._meta.get("misses", 0) + 1
                return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        with self._lock:
            path = self._key_to_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "key": key,
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + ttl if ttl else None,
            }

            with open(path, "w") as f:
                json.dump(data, f)

            self._meta["entries"][key] = time.time()
            self._save_meta()

    def delete(self, key: str) -> None:
        with self._lock:
            path = self._key_to_path(key)
            if path.exists():
                path.unlink()
            self._meta["entries"].pop(key, None)
            self._save_meta()

    def clear(self) -> None:
        with self._lock:
            import shutil
            for item in self._cache_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                elif item.name != "_meta.json":
                    item.unlink()
            self._meta = {"hits": 0, "misses": 0, "entries": {}}
            self._save_meta()

    def stats(self) -> dict:
        return {
            "backend": "file",
            "cache_dir": str(self._cache_dir),
            "entries": len(self._meta.get("entries", {})),
            "hits": self._meta.get("hits", 0),
            "misses": self._meta.get("misses", 0),
            "hit_rate": self._meta["hits"] / (self._meta["hits"] + self._meta["misses"])
            if (self._meta.get("hits", 0) + self._meta.get("misses", 0)) > 0
            else 0,
        }


class SQLiteCache(CacheBackend):
    """SQLite-based cache backend"""

    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(str(self._db_path))
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL,
                hit_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                name TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            )
        """)
        conn.execute("INSERT OR IGNORE INTO stats (name, value) VALUES ('hits', 0)")
        conn.execute("INSERT OR IGNORE INTO stats (name, value) VALUES ('misses', 0)")
        conn.commit()

    def get(self, key: str) -> Optional[str]:
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        )
        row = cursor.fetchone()

        if row is None:
            conn.execute("UPDATE stats SET value = value + 1 WHERE name = 'misses'")
            conn.commit()
            return None

        value, expires_at = row
        if expires_at and time.time() > expires_at:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.execute("UPDATE stats SET value = value + 1 WHERE name = 'misses'")
            conn.commit()
            return None

        conn.execute("UPDATE cache SET hit_count = hit_count + 1 WHERE key = ?", (key,))
        conn.execute("UPDATE stats SET value = value + 1 WHERE name = 'hits'")
        conn.commit()
        return value

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        conn = self._get_conn()
        expires_at = time.time() + ttl if ttl else None
        conn.execute(
            """
            INSERT OR REPLACE INTO cache (key, value, created_at, expires_at, hit_count)
            VALUES (?, ?, ?, ?, 0)
            """,
            (key, value, time.time(), expires_at),
        )
        conn.commit()

    def delete(self, key: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()

    def clear(self) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM cache")
        conn.execute("UPDATE stats SET value = 0")
        conn.commit()

    def stats(self) -> dict:
        conn = self._get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM cache")
        entries = cursor.fetchone()[0]

        cursor = conn.execute("SELECT name, value FROM stats")
        stats_data = dict(cursor.fetchall())

        hits = stats_data.get("hits", 0)
        misses = stats_data.get("misses", 0)
        total = hits + misses

        return {
            "backend": "sqlite",
            "db_path": str(self._db_path),
            "entries": entries,
            "hits": hits,
            "misses": misses,
            "hit_rate": hits / total if total > 0 else 0,
        }


class AnalysisCache:
    """
    High-level cache for analysis results.

    Caches API responses by image hash to avoid re-analyzing identical regions.
    """

    def __init__(
        self,
        backend: Optional[CacheBackend] = None,
        default_ttl: int = 86400,  # 24 hours
    ):
        self.backend = backend or MemoryCache()
        self.default_ttl = default_ttl

    @staticmethod
    def compute_image_hash(image_data: bytes) -> str:
        """Compute a hash for image data"""
        return hashlib.sha256(image_data).hexdigest()[:16]

    @staticmethod
    def compute_request_hash(
        image_hash: str,
        prompt_hash: str,
        model: str,
    ) -> str:
        """Compute a hash for the full request"""
        combined = f"{image_hash}:{prompt_hash}:{model}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def get_analysis(self, cache_key: str) -> Optional[dict]:
        """Get a cached analysis result"""
        value = self.backend.get(cache_key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def set_analysis(
        self,
        cache_key: str,
        result: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache an analysis result"""
        self.backend.set(
            cache_key,
            json.dumps(result),
            ttl or self.default_ttl,
        )

    def stats(self) -> dict:
        """Get cache statistics"""
        return self.backend.stats()


# Global cache instance
_global_cache: Optional[AnalysisCache] = None


def get_cache(
    backend_type: str = "memory",
    cache_dir: Optional[Path] = None,
) -> AnalysisCache:
    """Get or create the global cache instance"""
    global _global_cache

    if _global_cache is None:
        if backend_type == "memory":
            backend = MemoryCache()
        elif backend_type == "file":
            cache_dir = cache_dir or Path.home() / ".cache" / "drawing-analyzer"
            backend = FileCache(cache_dir)
        elif backend_type == "sqlite":
            cache_dir = cache_dir or Path.home() / ".cache" / "drawing-analyzer"
            backend = SQLiteCache(cache_dir / "cache.db")
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

        _global_cache = AnalysisCache(backend)

    return _global_cache
