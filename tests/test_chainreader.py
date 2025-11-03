"""Tests for ChainReader main API"""

import pytest

from chainreader.chainreader import ChainReader


def test_chainreader_initialization(sample_providers):
    """Test ChainReader initialization"""
    reader = ChainReader(chain_id=137, providers=sample_providers)

    assert reader.chain_id == 137
    assert reader.provider_manager is not None
    assert reader.cache_manager is not None
    assert reader.request_handler is not None


def test_chainreader_get_provider_stats(sample_providers):
    """Test getting provider stats"""
    reader = ChainReader(chain_id=137, providers=sample_providers, log_level="ERROR")

    stats = reader.get_provider_stats()
    assert "provider1" in stats
    assert "provider2" in stats
    assert "provider3" in stats


def test_chainreader_get_cache_stats(sample_providers):
    """Test getting cache stats"""
    reader = ChainReader(chain_id=137, providers=sample_providers, log_level="ERROR")

    stats = reader.get_cache_stats()
    assert "hits" in stats
    assert "misses" in stats
    assert "hit_rate" in stats
    assert "size" in stats


def test_chainreader_clear_cache(sample_providers):
    """Test clearing cache"""
    reader = ChainReader(chain_id=137, providers=sample_providers, log_level="ERROR")

    # Clear should not raise any errors
    reader.clear_cache()

    stats = reader.get_cache_stats()
    assert stats["size"] == 0


@pytest.mark.asyncio
async def test_chainreader_context_manager(sample_providers):
    """Test ChainReader as async context manager"""
    async with ChainReader(chain_id=137, providers=sample_providers, log_level="ERROR") as reader:
        assert reader is not None
        assert reader.chain_id == 137


def test_chainreader_custom_config(sample_providers):
    """Test ChainReader with custom configuration"""
    reader = ChainReader(
        chain_id=1,
        providers=sample_providers,
        cache_ttl_blocks=20,
        cache_ttl_latest=10,
        max_cache_size=5000,
        max_retries=5,
        retry_backoff_factor=3.0,
        failover_threshold=5,
        health_check_cooldown=600,
        request_timeout=60,
        log_level="DEBUG",
    )

    assert reader.chain_id == 1
    assert reader.cache_manager.cache_ttl_blocks == 20
    assert reader.cache_manager.cache_ttl_latest == 10
    assert reader.cache_manager.max_cache_size == 5000
    assert reader.request_handler.max_retries == 5
    assert reader.request_handler.retry_backoff_factor == 3.0
    assert reader.provider_manager.failover_threshold == 5
    assert reader.provider_manager.health_check_cooldown == 600
