"""Cache Manager for intelligent caching of blockchain data"""

import hashlib
import json
import logging
import time
from typing import Any

from chainreader.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Multi-strategy cache manager for blockchain data.

    Cache Strategies:
    - Permanent: Historical blocks, transaction receipts, contract bytecode (immutable)
    - Time-based TTL: Recent/latest data with expiration
    - No cache: Current pending data

    Phase 1 Implementation: In-memory cache only
    """

    def __init__(
        self,
        cache_ttl_blocks: int = 12,
        cache_ttl_latest: int = 5,
        max_cache_size: int = 10000,
    ):
        """
        Initialize the cache manager.

        Args:
            cache_ttl_blocks: Default TTL in seconds for recent block data (~12 blocks = 24s)
            cache_ttl_latest: TTL in seconds for 'latest' queries
            max_cache_size: Maximum number of entries to cache
        """
        self.cache_ttl_blocks = cache_ttl_blocks
        self.cache_ttl_latest = cache_ttl_latest
        self.max_cache_size = max_cache_size

        # Cache storage: {key: (value, expiration_timestamp or None)}
        self._cache: dict[str, tuple[Any, float | None]] = {}

        # Stats tracking
        self._hits = 0
        self._misses = 0

        logger.debug(
            f"Initialized CacheManager (ttl_blocks={cache_ttl_blocks}s, "
            f"ttl_latest={cache_ttl_latest}s, max_size={max_cache_size})"
        )

    def get(self, key: str) -> Any | None:
        """
        Retrieve a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            self._misses += 1
            logger.debug(f"Cache miss: {key}")
            return None

        value, expiration = self._cache[key]

        # Check if expired
        if expiration is not None and time.time() > expiration:
            # Remove expired entry
            del self._cache[key]
            self._misses += 1
            logger.debug(f"Cache expired: {key}")
            return None

        self._hits += 1
        logger.debug(f"Cache hit: {key}")
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Store a value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds, None for permanent caching

        Raises:
            CacheError: If cache operation fails
        """
        try:
            # Check cache size limit
            if len(self._cache) >= self.max_cache_size and key not in self._cache:
                self._evict_oldest()

            # Calculate expiration timestamp
            expiration = None if ttl is None else time.time() + ttl

            self._cache[key] = (value, expiration)

            ttl_str = "permanent" if ttl is None else f"{ttl}s"
            logger.debug(f"Cache set: {key} (ttl={ttl_str})")

        except Exception as e:
            raise CacheError(f"Failed to set cache entry: {e}") from e

    def invalidate(self, pattern: str) -> int:
        """
        Remove cache entries matching a pattern.

        Args:
            pattern: Pattern to match (simple substring match for Phase 1)

        Returns:
            Number of entries removed
        """
        keys_to_remove = [key for key in self._cache if pattern in key]
        count = len(keys_to_remove)

        for key in keys_to_remove:
            del self._cache[key]

        if count > 0:
            logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")

        return count

    def clear(self) -> None:
        """Clear all cache entries"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared cache ({count} entries)")

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit rate, size, and other metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "max_size": self.max_cache_size,
        }

    def generate_key(self, method: str, params: dict[str, Any]) -> str:
        """
        Generate a deterministic cache key from method and parameters.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Cache key string
        """
        # Sort params to ensure consistency
        params_str = json.dumps(params, sort_keys=True, default=str)
        key_input = f"{method}:{params_str}"

        # Use hash for shorter keys
        key_hash = hashlib.sha256(key_input.encode()).hexdigest()[:16]
        return f"{method}:{key_hash}"

    def determine_ttl(
        self,
        method: str,
        params: dict[str, Any],
        current_block: int | None = None,
    ) -> int | None:
        """
        Determine appropriate TTL for a cache entry based on data type.

        Args:
            method: RPC method name
            params: Method parameters
            current_block: Current block number (for immutability detection)

        Returns:
            TTL in seconds, or None for permanent caching
        """
        # Check if data is immutable (historical)
        if self._is_immutable(method, params, current_block):
            return None  # Permanent cache

        # Latest/recent data - short TTL
        # For get_block, check block_identifier instead of block
        if method == "get_block":
            block_param = params.get("block_identifier", "latest")
        else:
            block_param = params.get("block", "latest")

        if block_param in ["latest", "pending"]:
            return self.cache_ttl_latest

        # Recent block data - medium TTL
        return self.cache_ttl_blocks

    def _is_immutable(
        self,
        method: str,
        params: dict[str, Any],
        current_block: int | None = None,
    ) -> bool:
        """
        Determine if the requested data is immutable.

        Args:
            method: RPC method name
            params: Method parameters
            current_block: Current block number

        Returns:
            True if data is immutable and can be cached permanently
        """
        # Transaction receipts are always immutable
        if method in ["get_transaction_receipt", "get_transaction"]:
            return True

        # Check for historical blocks
        if method == "get_block":
            block_identifier = params.get("block_identifier")
            if isinstance(block_identifier, int) and current_block is not None:
                # Consider blocks older than 12 blocks as final (immutable)
                if block_identifier < current_block - 12:
                    return True

        # Check for contract calls on historical blocks
        if method == "call_contract":
            block = params.get("block", "latest")
            if isinstance(block, int) and current_block is not None:
                if block < current_block - 12:
                    return True

        # Check for historical logs
        if method == "get_logs":
            to_block = params.get("to_block", "latest")
            if isinstance(to_block, int) and current_block is not None:
                if to_block < current_block - 12:
                    return True

        return False

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry to make room for new ones"""
        if not self._cache:
            return

        # Find entries with expiration times and evict the one expiring soonest
        # If none have expiration, evict a random one (in practice, first one)
        entries_with_expiration = [
            (key, exp) for key, (_, exp) in self._cache.items() if exp is not None
        ]

        if entries_with_expiration:
            # Evict the entry expiring soonest
            oldest_key = min(entries_with_expiration, key=lambda x: x[1])[0]
        else:
            # Evict first entry (arbitrary choice)
            oldest_key = next(iter(self._cache))

        del self._cache[oldest_key]
        logger.debug(f"Evicted cache entry to make room: {oldest_key}")
