"""Tests for CacheManager"""

import time

from chainreader.cache_manager import CacheManager


def test_cache_initialization():
    """Test CacheManager initialization"""
    cache = CacheManager(cache_ttl_blocks=10, cache_ttl_latest=5, max_cache_size=100)
    assert cache.cache_ttl_blocks == 10
    assert cache.cache_ttl_latest == 5
    assert cache.max_cache_size == 100


def test_cache_get_set():
    """Test basic cache get and set"""
    cache = CacheManager()

    # Cache miss
    assert cache.get("test_key") is None

    # Cache set and hit
    cache.set("test_key", "test_value", ttl=60)
    assert cache.get("test_key") == "test_value"


def test_cache_permanent_storage():
    """Test permanent caching (no TTL)"""
    cache = CacheManager()

    cache.set("permanent_key", "permanent_value", ttl=None)
    assert cache.get("permanent_key") == "permanent_value"

    # Even after waiting, should still be there
    time.sleep(0.1)
    assert cache.get("permanent_key") == "permanent_value"


def test_cache_expiration():
    """Test that cached values expire after TTL"""
    cache = CacheManager()

    cache.set("expiring_key", "expiring_value", ttl=1)
    assert cache.get("expiring_key") == "expiring_value"

    # Wait for expiration
    time.sleep(1.1)
    assert cache.get("expiring_key") is None


def test_cache_stats():
    """Test cache statistics tracking"""
    cache = CacheManager()

    # Initial stats
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 0.0
    assert stats["size"] == 0

    # Add some data
    cache.set("key1", "value1")
    cache.get("key1")  # Hit
    cache.get("key2")  # Miss

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5
    assert stats["size"] == 1


def test_cache_invalidate():
    """Test cache invalidation by pattern"""
    cache = CacheManager()

    cache.set("user:1:balance", 100)
    cache.set("user:2:balance", 200)
    cache.set("contract:1:data", "data")

    # Invalidate all user balances
    count = cache.invalidate("user:")
    assert count == 2
    assert cache.get("user:1:balance") is None
    assert cache.get("user:2:balance") is None
    assert cache.get("contract:1:data") == "data"


def test_cache_clear():
    """Test clearing all cache entries"""
    cache = CacheManager()

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    assert cache.get_stats()["size"] == 3

    cache.clear()
    assert cache.get_stats()["size"] == 0
    assert cache.get("key1") is None


def test_generate_key_consistency():
    """Test that cache key generation is consistent"""
    cache = CacheManager()

    params1 = {"address": "0x123", "block": "latest"}
    params2 = {"block": "latest", "address": "0x123"}  # Different order

    key1 = cache.generate_key("get_balance", params1)
    key2 = cache.generate_key("get_balance", params2)

    # Should be the same despite parameter order
    assert key1 == key2


def test_generate_key_uniqueness():
    """Test that different requests generate different keys"""
    cache = CacheManager()

    key1 = cache.generate_key("get_balance", {"address": "0x123"})
    key2 = cache.generate_key("get_balance", {"address": "0x456"})
    key3 = cache.generate_key("get_block", {"block_identifier": "latest"})

    # All should be different
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3


def test_determine_ttl_immutable_receipt():
    """Test that transaction receipts are cached permanently"""
    cache = CacheManager()

    ttl = cache.determine_ttl("get_transaction_receipt", {"tx_hash": "0x123"})
    assert ttl is None  # Permanent


def test_determine_ttl_latest_block():
    """Test TTL for latest block queries"""
    cache = CacheManager(cache_ttl_latest=5)

    ttl = cache.determine_ttl("get_balance", {"address": "0x123", "block": "latest"})
    assert ttl == 5


def test_determine_ttl_historical_block():
    """Test that historical blocks are cached permanently"""
    cache = CacheManager()

    # Historical block (more than 12 blocks old)
    ttl = cache.determine_ttl(
        "get_block",
        {"block_identifier": 1000},
        current_block=2000,
    )
    assert ttl is None  # Permanent


def test_determine_ttl_recent_block():
    """Test TTL for recent block queries"""
    cache = CacheManager(cache_ttl_blocks=12)

    # Recent block (less than 12 blocks old)
    ttl = cache.determine_ttl(
        "get_block",
        {"block_identifier": 1995},
        current_block=2000,
    )
    assert ttl == 12


def test_is_immutable_transaction_receipt():
    """Test immutability detection for transaction receipts"""
    cache = CacheManager()

    assert cache._is_immutable("get_transaction_receipt", {}) is True
    assert cache._is_immutable("get_transaction", {}) is True


def test_is_immutable_historical_block():
    """Test immutability detection for historical blocks"""
    cache = CacheManager()

    # Old block
    assert (
        cache._is_immutable(
            "get_block",
            {"block_identifier": 1000},
            current_block=2000,
        )
        is True
    )

    # Recent block
    assert (
        cache._is_immutable(
            "get_block",
            {"block_identifier": 1995},
            current_block=2000,
        )
        is False
    )


def test_is_immutable_contract_call():
    """Test immutability detection for contract calls"""
    cache = CacheManager()

    # Historical call
    assert (
        cache._is_immutable(
            "call_contract",
            {"address": "0x123", "method": "balanceOf", "block": 1000},
            current_block=2000,
        )
        is True
    )

    # Latest call
    assert (
        cache._is_immutable(
            "call_contract",
            {"address": "0x123", "method": "balanceOf", "block": "latest"},
            current_block=2000,
        )
        is False
    )


def test_cache_eviction():
    """Test that cache evicts old entries when max size reached"""
    cache = CacheManager(max_cache_size=3)

    cache.set("key1", "value1", ttl=10)
    cache.set("key2", "value2", ttl=20)
    cache.set("key3", "value3", ttl=30)

    assert cache.get_stats()["size"] == 3

    # Adding 4th item should evict the one expiring soonest (key1)
    cache.set("key4", "value4", ttl=40)

    assert cache.get_stats()["size"] == 3
    assert cache.get("key1") is None  # Evicted
    assert cache.get("key4") == "value4"  # New one added


def test_cache_eviction_permanent_entries():
    """Test eviction when all entries are permanent"""
    cache = CacheManager(max_cache_size=2)

    cache.set("key1", "value1", ttl=None)  # Permanent
    cache.set("key2", "value2", ttl=None)  # Permanent

    # Adding 3rd permanent entry should evict one (arbitrary)
    cache.set("key3", "value3", ttl=None)

    assert cache.get_stats()["size"] == 2
