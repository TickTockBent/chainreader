"""Request Handler for optimized request execution with caching and retries"""

from __future__ import annotations

import logging
import time
from typing import Any

from chainreader.cache_manager import CacheManager
from chainreader.chain_client import ChainClient
from chainreader.exceptions import AllProvidersFailedError, ProviderError, RateLimitError
from chainreader.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


class RequestHandler:
    """
    Handles request execution with caching, retries, and provider failover.

    Responsibilities:
    - Check cache before making RPC calls
    - Execute requests with retry logic
    - Handle provider failover on errors
    - Cache successful results with appropriate TTL
    - Track request/response metrics
    """

    def __init__(
        self,
        provider_manager: ProviderManager,
        cache_manager: CacheManager,
        chain_id: int,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        request_timeout: int = 30,
    ):
        """
        Initialize the request handler.

        Args:
            provider_manager: Provider manager instance
            cache_manager: Cache manager instance
            chain_id: Network chain ID
            max_retries: Maximum number of retries per request
            retry_backoff_factor: Exponential backoff factor for retries
            request_timeout: Request timeout in seconds
        """
        self.provider_manager = provider_manager
        self.cache_manager = cache_manager
        self.chain_id = chain_id
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.request_timeout = request_timeout

        # Track current block number for cache TTL decisions
        self._current_block: int | None = None
        self._current_block_time: float = 0.0
        self._block_cache_ttl = 10.0  # Cache current block number for 10 seconds

        logger.debug(
            f"Initialized RequestHandler (max_retries={max_retries}, "
            f"backoff={retry_backoff_factor})"
        )

    async def execute(
        self,
        method: str,
        params: dict[str, Any],
        use_cache: bool = True,
    ) -> Any:
        """
        Execute a request with caching and failover.

        Args:
            method: Method name (e.g., 'get_balance', 'get_block')
            params: Method parameters
            use_cache: Whether to use cache for this request

        Returns:
            Result from the method execution

        Raises:
            AllProvidersFailedError: If all providers fail
            Various other exceptions depending on the method
        """
        # Generate cache key
        cache_key = self.cache_manager.generate_key(method, params)

        # Check cache first
        if use_cache:
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Returning cached result for {method}")
                return cached_result

        # Execute request with retry and failover
        result = await self._execute_with_failover(method, params)

        # Cache the result if caching is enabled
        if use_cache:
            await self._cache_result(method, params, cache_key, result)

        return result

    async def _execute_with_failover(
        self,
        method: str,
        params: dict[str, Any],
    ) -> Any:
        """
        Execute request with provider failover.

        Tries each healthy provider until one succeeds or all fail.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            Result from successful execution

        Raises:
            AllProvidersFailedError: If all providers fail
        """
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            try:
                # Get next provider
                provider = self.provider_manager.get_provider()
                logger.debug(
                    f"Attempting {method} with provider '{provider.name}' (attempt {attempts + 1})"
                )

                # Create client for this provider
                client = ChainClient(
                    provider_url=provider.url,
                    chain_id=self.chain_id,
                    request_timeout=self.request_timeout,
                )

                # Execute the request and measure latency
                start_time = time.time()
                result = await self._call_client_method(client, method, params)
                latency = time.time() - start_time

                # Mark provider success
                self.provider_manager.mark_success(provider.name, latency)

                logger.debug(
                    f"Request succeeded with provider '{provider.name}' "
                    f"(latency: {latency:.3f}s)"
                )

                return result

            except ProviderError as e:
                last_error = e
                attempts += 1

                # Mark provider failure
                if hasattr(e, "provider_name"):
                    provider_name = e.provider_name
                else:
                    provider_name = provider.name if "provider" in locals() else "unknown"

                self.provider_manager.mark_failure(provider_name, e)

                # Check if it's a rate limit error
                if isinstance(e, RateLimitError):
                    logger.warning(f"Rate limit hit on provider '{provider_name}'")

                # If we haven't exhausted retries, continue to next provider
                if attempts < self.max_retries:
                    logger.info(
                        f"Retrying with different provider (attempt {attempts + 1}/{self.max_retries})"
                    )
                    continue

            except AllProvidersFailedError:
                # All providers are unhealthy, no point in retrying
                raise

            except Exception as e:
                # Unexpected error
                last_error = e
                attempts += 1
                logger.error(f"Unexpected error during request: {e}", exc_info=True)

                if attempts < self.max_retries:
                    logger.info(f"Retrying after unexpected error (attempt {attempts + 1})")
                    continue

        # All retries exhausted
        raise AllProvidersFailedError(
            f"Request failed after {attempts} attempts across multiple providers. "
            f"Last error: {last_error}"
        )

    async def _call_client_method(
        self,
        client: ChainClient,
        method: str,
        params: dict[str, Any],
    ) -> Any:
        """
        Call the appropriate ChainClient method based on method name.

        Args:
            client: ChainClient instance
            method: Method name
            params: Method parameters

        Returns:
            Result from the client method
        """
        # Map method names to client methods
        if method == "get_balance":
            return await client.get_balance(
                address=params["address"],
                block=params.get("block", "latest"),
            )
        elif method == "get_block":
            return await client.get_block(
                block_identifier=params["block_identifier"],
            )
        elif method == "get_transaction":
            return await client.get_transaction(tx_hash=params["tx_hash"])
        elif method == "get_transaction_receipt":
            return await client.get_transaction_receipt(tx_hash=params["tx_hash"])
        elif method == "call_contract":
            return await client.call_contract(
                address=params["address"],
                abi=params["abi"],
                method=params["method"],
                args=params.get("args", []),
                block=params.get("block", "latest"),
            )
        elif method == "get_logs":
            return await client.get_logs(
                address=params.get("address"),
                topics=params.get("topics"),
                from_block=params.get("from_block", 0),
                to_block=params.get("to_block", "latest"),
            )
        elif method == "get_block_number":
            return await client.get_block_number()
        else:
            raise ValueError(f"Unknown method: {method}")

    async def _cache_result(
        self,
        method: str,
        params: dict[str, Any],
        cache_key: str,
        result: Any,
    ) -> None:
        """
        Cache the result with appropriate TTL.

        Args:
            method: Method name
            params: Method parameters
            cache_key: Cache key
            result: Result to cache
        """
        try:
            # Get current block number if not cached
            current_block = await self._get_current_block()

            # Determine TTL based on data type
            ttl = self.cache_manager.determine_ttl(method, params, current_block)

            # Store in cache
            self.cache_manager.set(cache_key, result, ttl)

        except Exception as e:
            # Don't fail the request if caching fails
            logger.warning(f"Failed to cache result: {e}")

    async def _get_current_block(self) -> int | None:
        """
        Get current block number, with local caching.

        Returns:
            Current block number or None if unavailable
        """
        try:
            # Check if we have a recent cached block number
            if (
                self._current_block is not None
                and time.time() - self._current_block_time < self._block_cache_ttl
            ):
                return self._current_block

            # Fetch current block number (without caching to avoid recursion)
            provider = self.provider_manager.get_provider()
            client = ChainClient(
                provider_url=provider.url,
                chain_id=self.chain_id,
                request_timeout=self.request_timeout,
            )

            block_number = await client.get_block_number()

            # Update cached block number
            self._current_block = block_number
            self._current_block_time = time.time()

            return block_number

        except Exception as e:
            logger.warning(f"Failed to fetch current block number for cache TTL: {e}")
            return None
