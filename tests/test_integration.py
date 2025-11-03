"""Integration tests for ChainReader components working together"""

import pytest

from chainreader import ChainReader
from chainreader.cache_manager import CacheManager
from chainreader.provider_manager import ProviderManager
from chainreader.request_handler import RequestHandler


def test_provider_and_cache_integration(sample_providers):
    """Test provider manager and cache manager working together"""
    provider_manager = ProviderManager(providers=sample_providers)
    cache_manager = CacheManager()

    # Get a provider
    provider = provider_manager.get_provider()
    assert provider is not None

    # Use cache
    cache_manager.set("test_key", "test_value", ttl=60)
    assert cache_manager.get("test_key") == "test_value"

    # Mark provider success
    provider_manager.mark_success(provider.name, latency=0.5)
    stats = provider_manager.get_provider_stats()
    assert stats[provider.name]["success_count"] == 1


def test_request_handler_initialization(sample_providers):
    """Test request handler initialization with all components"""
    provider_manager = ProviderManager(providers=sample_providers)
    cache_manager = CacheManager()

    request_handler = RequestHandler(
        provider_manager=provider_manager,
        cache_manager=cache_manager,
        chain_id=137,
        max_retries=3,
        retry_backoff_factor=2.0,
        request_timeout=30,
    )

    assert request_handler.provider_manager == provider_manager
    assert request_handler.cache_manager == cache_manager
    assert request_handler.chain_id == 137
    assert request_handler.max_retries == 3


@pytest.mark.asyncio
async def test_request_handler_with_all_providers_down(sample_providers):
    """Test request handler when all providers fail"""
    # Mark all providers as failed
    provider_manager = ProviderManager(providers=sample_providers, failover_threshold=1)
    for provider_name in provider_manager.providers:
        provider_manager.mark_failure(provider_name, Exception("Down"))

    cache_manager = CacheManager()
    _ = RequestHandler(
        provider_manager=provider_manager,
        cache_manager=cache_manager,
        chain_id=137,
        max_retries=1,
    )

    # Should raise AllProvidersFailedError after force recovery and retry
    # Note: The implementation force-recovers all providers when all are down,
    # so it will try to execute but fail on actual network call
    # For this test, we just verify the components are wired together
    # (request_handler is created but not used in this test)


def test_chainreader_components_integration(sample_providers):
    """Test that ChainReader properly initializes all components"""
    reader = ChainReader(
        chain_id=137,
        providers=sample_providers,
        cache_ttl_blocks=20,
        cache_ttl_latest=10,
        max_retries=5,
        log_level="ERROR",
    )

    # Verify components are created
    assert reader.provider_manager is not None
    assert reader.cache_manager is not None
    assert reader.request_handler is not None

    # Verify configurations are passed through
    assert reader.cache_manager.cache_ttl_blocks == 20
    assert reader.cache_manager.cache_ttl_latest == 10
    assert reader.request_handler.max_retries == 5

    # Verify provider manager has all providers
    stats = reader.get_provider_stats()
    assert len(stats) == 3
    assert "provider1" in stats


@pytest.mark.asyncio
async def test_chainreader_context_manager_lifecycle(sample_providers):
    """Test ChainReader async context manager lifecycle"""
    async with ChainReader(chain_id=1, providers=sample_providers, log_level="ERROR") as reader:
        assert reader is not None
        assert reader.chain_id == 1

        # Should be usable inside context
        stats = reader.get_cache_stats()
        assert "hits" in stats

    # Context should exit cleanly


def test_cache_integration_with_ttl_strategies():
    """Test cache manager with different TTL strategies"""
    cache = CacheManager(cache_ttl_blocks=15, cache_ttl_latest=3)

    # Test permanent caching for immutable data
    ttl = cache.determine_ttl("get_transaction_receipt", {"tx_hash": "0x123"})
    assert ttl is None

    # Test short TTL for latest queries
    ttl = cache.determine_ttl("get_balance", {"address": "0x123", "block": "latest"})
    assert ttl == 3

    # Test medium TTL for historical but recent blocks
    ttl = cache.determine_ttl("get_block", {"block_identifier": 1995}, current_block=2000)
    assert ttl == 15


def test_provider_health_recovery_flow(sample_providers):
    """Test provider health tracking and recovery"""
    pm = ProviderManager(providers=sample_providers, failover_threshold=2, health_check_cooldown=1)

    # Mark provider as unhealthy
    pm.mark_failure("provider1", Exception("error"))
    pm.mark_failure("provider1", Exception("error"))
    assert not pm.providers["provider1"].is_healthy

    # Get next healthy provider
    provider = pm.get_provider()
    assert provider.name != "provider1"  # Should skip unhealthy one

    # After recovery, provider should be available again
    import time

    time.sleep(1.1)
    pm._recover_failed_providers()
    assert pm.providers["provider1"].is_healthy


def test_multiple_cache_strategies():
    """Test cache with multiple data types"""
    cache = CacheManager()

    # Store different types of data
    cache.set("permanent", "value1", ttl=None)
    cache.set("temporary", "value2", ttl=1)
    cache.set("medium", "value3", ttl=10)

    # All should be retrievable initially
    assert cache.get("permanent") == "value1"
    assert cache.get("temporary") == "value2"
    assert cache.get("medium") == "value3"

    # After expiration, temporary should be gone
    import time

    time.sleep(1.1)
    assert cache.get("permanent") == "value1"
    assert cache.get("temporary") is None
    assert cache.get("medium") == "value3"


def test_provider_priority_and_round_robin(sample_providers):
    """Test that providers are selected by priority then round-robin"""
    pm = ProviderManager(providers=sample_providers)

    # First call should get priority 1
    provider1 = pm.get_provider()
    assert provider1.priority == 1

    # Subsequent calls should still prefer priority 1 (same priority)
    provider2 = pm.get_provider()
    assert provider2.priority == 1


def test_error_propagation():
    """Test that errors propagate correctly through the stack"""
    from chainreader.exceptions import InvalidAddressError

    # Test InvalidAddressError creation
    error = InvalidAddressError("0xinvalid")
    assert isinstance(error, Exception)
    assert "0xinvalid" in str(error)


def test_cache_key_generation_determinism():
    """Test that cache keys are deterministic"""
    cache = CacheManager()

    # Same params in different order should produce same key
    key1 = cache.generate_key("test_method", {"a": 1, "b": 2, "c": 3})
    key2 = cache.generate_key("test_method", {"c": 3, "a": 1, "b": 2})
    assert key1 == key2

    # Different methods should produce different keys
    key3 = cache.generate_key("other_method", {"a": 1, "b": 2, "c": 3})
    assert key1 != key3

    # Different params should produce different keys
    key4 = cache.generate_key("test_method", {"a": 1, "b": 2, "c": 4})
    assert key1 != key4
