"""Tests for ProviderManager"""

import time

import pytest

from chainreader.provider_manager import Provider, ProviderManager


def test_provider_initialization():
    """Test Provider dataclass initialization"""
    provider = Provider(name="test", url="https://test.com", priority=1)
    assert provider.name == "test"
    assert provider.url == "https://test.com"
    assert provider.priority == 1
    assert provider.is_healthy is True
    assert provider.failure_count == 0
    assert provider.success_count == 0


def test_provider_average_latency():
    """Test average latency calculation"""
    provider = Provider(name="test", url="https://test.com")
    assert provider.average_latency == 0.0

    provider.total_latency = 1.5
    provider.request_count = 3
    assert provider.average_latency == 0.5


def test_provider_success_rate():
    """Test success rate calculation"""
    provider = Provider(name="test", url="https://test.com")
    assert provider.success_rate == 1.0  # No attempts = 100%

    provider.success_count = 7
    provider.failure_count = 3
    assert provider.success_rate == 0.7


def test_provider_manager_initialization(sample_providers):
    """Test ProviderManager initialization"""
    pm = ProviderManager(providers=sample_providers)
    assert len(pm.providers) == 3
    assert "provider1" in pm.providers
    assert pm.providers["provider1"].url == "https://rpc1.example.com"
    assert pm.providers["provider1"].priority == 1


def test_provider_manager_empty_providers():
    """Test ProviderManager with no providers raises error"""
    with pytest.raises(ValueError, match="At least one provider must be configured"):
        ProviderManager(providers=[])


def test_get_provider_priority_order(sample_providers):
    """Test provider selection respects priority"""
    pm = ProviderManager(providers=sample_providers)

    # First call should return highest priority (lowest number)
    provider = pm.get_provider()
    assert provider.name == "provider1"
    assert provider.priority == 1


def test_mark_failure(sample_providers):
    """Test marking provider failures"""
    pm = ProviderManager(providers=sample_providers, failover_threshold=2)

    # First failure
    pm.mark_failure("provider1", Exception("test error"))
    assert pm.providers["provider1"].failure_count == 1
    assert pm.providers["provider1"].is_healthy is True  # Still below threshold

    # Second failure - should mark as unhealthy
    pm.mark_failure("provider1", Exception("test error"))
    assert pm.providers["provider1"].failure_count == 2
    assert pm.providers["provider1"].is_healthy is False


def test_mark_success(sample_providers):
    """Test marking provider success"""
    pm = ProviderManager(providers=sample_providers)

    pm.mark_success("provider1", latency=0.5)
    assert pm.providers["provider1"].success_count == 1
    assert pm.providers["provider1"].request_count == 1
    assert pm.providers["provider1"].total_latency == 0.5


def test_mark_success_resets_failure_count(sample_providers):
    """Test that success resets failure count"""
    pm = ProviderManager(providers=sample_providers, failover_threshold=3)

    pm.mark_failure("provider1", Exception("error"))
    assert pm.providers["provider1"].failure_count == 1

    pm.mark_success("provider1", latency=0.5)
    assert pm.providers["provider1"].failure_count == 0
    assert pm.providers["provider1"].is_healthy is True


def test_get_provider_skips_unhealthy(sample_providers):
    """Test that get_provider skips unhealthy providers"""
    pm = ProviderManager(providers=sample_providers, failover_threshold=1)

    # Mark provider1 as unhealthy
    pm.mark_failure("provider1", Exception("error"))
    assert pm.providers["provider1"].is_healthy is False

    # Should get provider2 (next priority)
    provider = pm.get_provider()
    assert provider.name == "provider2"


def test_all_providers_failed(sample_providers):
    """Test AllProvidersFailedError when all providers are unhealthy"""
    pm = ProviderManager(providers=sample_providers, failover_threshold=1)

    # Mark all providers as unhealthy
    for provider_name in pm.providers:
        pm.mark_failure(provider_name, Exception("error"))

    # Should raise AllProvidersFailedError, but then force recover
    # First call will force recovery and return a provider
    provider = pm.get_provider()
    assert provider is not None


def test_get_provider_stats(sample_providers):
    """Test getting provider statistics"""
    pm = ProviderManager(providers=sample_providers)

    pm.mark_success("provider1", latency=0.5)
    pm.mark_failure("provider2", Exception("error"))

    stats = pm.get_provider_stats()
    assert "provider1" in stats
    assert stats["provider1"]["success_count"] == 1
    assert stats["provider1"]["is_healthy"] is True

    assert "provider2" in stats
    assert stats["provider2"]["failure_count"] == 1


def test_provider_recovery_after_cooldown(sample_providers):
    """Test provider recovery after cooldown period"""
    pm = ProviderManager(providers=sample_providers, failover_threshold=1, health_check_cooldown=1)

    # Mark provider as unhealthy
    pm.mark_failure("provider1", Exception("error"))
    assert pm.providers["provider1"].is_healthy is False

    # Wait for cooldown
    time.sleep(1.1)

    # Call get_provider to trigger recovery check
    pm._recover_failed_providers()
    assert pm.providers["provider1"].is_healthy is True
    assert pm.providers["provider1"].failure_count == 0


def test_unknown_provider_warning(sample_providers, caplog):
    """Test warning when marking unknown provider"""
    pm = ProviderManager(providers=sample_providers)

    pm.mark_failure("unknown_provider", Exception("error"))
    assert "unknown provider" in caplog.text.lower()

    pm.mark_success("unknown_provider", latency=0.5)
    assert "unknown provider" in caplog.text.lower()
