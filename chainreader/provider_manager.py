"""Provider Manager for handling multiple RPC providers with failover and health tracking"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from chainreader.exceptions import AllProvidersFailedError

logger = logging.getLogger(__name__)


@dataclass
class Provider:
    """Represents an RPC provider with health and performance metrics"""

    name: str
    url: str
    priority: int = 1
    is_healthy: bool = True
    failure_count: int = 0
    last_failure_time: float | None = None
    success_count: int = 0
    total_latency: float = 0.0
    request_count: int = 0
    last_used_time: float = field(default_factory=time.time)

    @property
    def average_latency(self) -> float:
        """Calculate average latency for this provider"""
        if self.request_count == 0:
            return 0.0
        return self.total_latency / self.request_count

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this provider"""
        total_attempts = self.success_count + self.failure_count
        if total_attempts == 0:
            return 1.0
        return self.success_count / total_attempts


class ProviderManager:
    """
    Manages multiple RPC providers with automatic failover and health tracking.

    Responsibilities:
    - Maintain list of configured providers
    - Track health status and latency for each
    - Implement priority-based provider selection with round-robin fallback
    - Handle provider failover on errors
    - Periodic health recovery for failed providers
    """

    def __init__(
        self,
        providers: list[dict[str, Any]],
        failover_threshold: int = 3,
        health_check_cooldown: int = 300,
    ):
        """
        Initialize the Provider Manager.

        Args:
            providers: List of provider configs with 'name', 'url', and optional 'priority'
            failover_threshold: Number of consecutive failures before marking provider unhealthy
            health_check_cooldown: Seconds to wait before re-enabling a failed provider
        """
        if not providers:
            raise ValueError("At least one provider must be configured")

        self.providers: dict[str, Provider] = {}
        self.failover_threshold = failover_threshold
        self.health_check_cooldown = health_check_cooldown
        self._current_provider_index = 0

        # Initialize providers
        for idx, provider_config in enumerate(providers):
            name = provider_config.get("name", f"provider_{idx}")
            url = provider_config["url"]
            priority = provider_config.get("priority", 1)

            self.providers[name] = Provider(name=name, url=url, priority=priority)

        logger.info(f"Initialized ProviderManager with {len(self.providers)} provider(s)")

    def get_provider(self) -> Provider:
        """
        Get the next healthy provider based on priority and round-robin.

        Returns:
            Provider: A healthy provider to use

        Raises:
            AllProvidersFailedError: If no healthy providers are available
        """
        # First, try to recover any providers that have passed the cooldown period
        self._recover_failed_providers()

        # Get all healthy providers sorted by priority (lower number = higher priority)
        healthy_providers = [p for p in self.providers.values() if p.is_healthy]

        if not healthy_providers:
            # Try to recover all providers once
            self._force_recover_all_providers()
            healthy_providers = [p for p in self.providers.values() if p.is_healthy]

            if not healthy_providers:
                raise AllProvidersFailedError(
                    f"All {len(self.providers)} configured RPC providers are currently unhealthy"
                )

        # Sort by priority, then by last used time (to implement round-robin within same priority)
        healthy_providers.sort(key=lambda p: (p.priority, p.last_used_time))

        # Select the next provider
        provider = healthy_providers[0]
        provider.last_used_time = time.time()

        logger.debug(f"Selected provider: {provider.name}")
        return provider

    def mark_failure(self, provider_name: str, error: Exception | None = None) -> None:
        """
        Record a provider failure.

        Args:
            provider_name: Name of the provider that failed
            error: Optional exception that caused the failure
        """
        if provider_name not in self.providers:
            logger.warning(f"Attempted to mark failure for unknown provider: {provider_name}")
            return

        provider = self.providers[provider_name]
        provider.failure_count += 1
        provider.last_failure_time = time.time()

        logger.warning(
            f"Provider '{provider_name}' failed (failure count: {provider.failure_count}): {error}"
        )

        # Mark as unhealthy if threshold exceeded
        if provider.failure_count >= self.failover_threshold:
            provider.is_healthy = False
            logger.error(
                f"Provider '{provider_name}' marked as unhealthy after "
                f"{provider.failure_count} failures"
            )

    def mark_success(self, provider_name: str, latency: float) -> None:
        """
        Record a successful provider request.

        Args:
            provider_name: Name of the provider that succeeded
            latency: Request latency in seconds
        """
        if provider_name not in self.providers:
            logger.warning(f"Attempted to mark success for unknown provider: {provider_name}")
            return

        provider = self.providers[provider_name]
        provider.success_count += 1
        provider.request_count += 1
        provider.total_latency += latency

        # Reset failure count on success
        if provider.failure_count > 0:
            logger.info(f"Provider '{provider_name}' recovered, resetting failure count")
            provider.failure_count = 0

        # Ensure provider is marked as healthy
        if not provider.is_healthy:
            provider.is_healthy = True
            logger.info(f"Provider '{provider_name}' marked as healthy after successful request")

        logger.debug(f"Provider '{provider_name}' success (latency: {latency:.3f}s)")

    def get_provider_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get health and performance statistics for all providers.

        Returns:
            Dictionary mapping provider names to their stats
        """
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = {
                "url": provider.url,
                "priority": provider.priority,
                "is_healthy": provider.is_healthy,
                "success_count": provider.success_count,
                "failure_count": provider.failure_count,
                "success_rate": provider.success_rate,
                "average_latency": provider.average_latency,
                "request_count": provider.request_count,
                "last_failure_time": provider.last_failure_time,
            }
        return stats

    def _recover_failed_providers(self) -> None:
        """Check if any failed providers can be recovered based on cooldown period"""
        current_time = time.time()

        for provider in self.providers.values():
            if not provider.is_healthy and provider.last_failure_time:
                time_since_failure = current_time - provider.last_failure_time

                if time_since_failure >= self.health_check_cooldown:
                    logger.info(
                        f"Attempting to recover provider '{provider.name}' after "
                        f"{time_since_failure:.0f}s cooldown"
                    )
                    provider.is_healthy = True
                    provider.failure_count = 0

    def _force_recover_all_providers(self) -> None:
        """Force recovery of all providers (used when all providers are down)"""
        logger.warning("All providers are unhealthy, forcing recovery of all providers")
        for provider in self.providers.values():
            provider.is_healthy = True
            provider.failure_count = 0
