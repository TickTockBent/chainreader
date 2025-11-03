"""ChainReader - Main public API for blockchain data access"""

from __future__ import annotations

import logging
from typing import Any

from chainreader.cache_manager import CacheManager
from chainreader.provider_manager import ProviderManager
from chainreader.request_handler import RequestHandler

logger = logging.getLogger(__name__)


class ChainReader:
    """
    Main interface for reading blockchain data with intelligent caching and provider management.

    Features:
    - Multiple RPC provider support with automatic failover
    - Intelligent caching of immutable and recent data
    - Retry logic with exponential backoff
    - Provider health tracking

    Example:
        ```python
        reader = ChainReader(
            chain_id=137,  # Polygon
            providers=[
                {'name': 'infura', 'url': 'https://polygon-mainnet.infura.io/v3/KEY'},
                {'name': 'alchemy', 'url': 'https://polygon-mainnet.g.alchemy.com/v2/KEY'},
            ]
        )

        async with reader:
            balance = await reader.get_balance('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb')
            block = await reader.get_block('latest')
        ```
    """

    def __init__(
        self,
        chain_id: int,
        providers: list[dict[str, Any]],
        cache_ttl_blocks: int = 12,
        cache_ttl_latest: int = 5,
        max_cache_size: int = 10000,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        failover_threshold: int = 3,
        health_check_cooldown: int = 300,
        request_timeout: int = 30,
        log_level: str = "INFO",
    ):
        """
        Initialize ChainReader.

        Args:
            chain_id: Network chain ID (e.g., 1 for Ethereum, 137 for Polygon)
            providers: List of provider configs with 'name', 'url', and optional 'priority'
            cache_ttl_blocks: TTL in seconds for recent block data (default: 12s)
            cache_ttl_latest: TTL in seconds for 'latest' queries (default: 5s)
            max_cache_size: Maximum number of cached entries (default: 10000)
            max_retries: Maximum retry attempts per request (default: 3)
            retry_backoff_factor: Exponential backoff factor (default: 2.0)
            failover_threshold: Failures before marking provider unhealthy (default: 3)
            health_check_cooldown: Seconds before re-enabling failed provider (default: 300)
            request_timeout: RPC request timeout in seconds (default: 30)
            log_level: Logging level (default: 'INFO')
        """
        self.chain_id = chain_id

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Initialize components
        self.provider_manager = ProviderManager(
            providers=providers,
            failover_threshold=failover_threshold,
            health_check_cooldown=health_check_cooldown,
        )

        self.cache_manager = CacheManager(
            cache_ttl_blocks=cache_ttl_blocks,
            cache_ttl_latest=cache_ttl_latest,
            max_cache_size=max_cache_size,
        )

        self.request_handler = RequestHandler(
            provider_manager=self.provider_manager,
            cache_manager=self.cache_manager,
            chain_id=chain_id,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
            request_timeout=request_timeout,
        )

        logger.info(
            f"Initialized ChainReader for chain_id={chain_id} " f"with {len(providers)} provider(s)"
        )

    async def get_balance(self, address: str, block: str | int = "latest") -> int:
        """
        Get the balance of an address.

        Args:
            address: Ethereum address (hex string)
            block: Block number, hash, or 'latest'/'earliest' (default: 'latest')

        Returns:
            Balance in wei (as integer)

        Raises:
            InvalidAddressError: If address format is invalid
            AllProvidersFailedError: If all providers fail
        """
        params = {"address": address, "block": block}
        return await self.request_handler.execute("get_balance", params)

    async def get_block(self, block_identifier: str | int = "latest") -> dict[str, Any]:
        """
        Get block data.

        Args:
            block_identifier: Block number, hash, or 'latest'/'earliest' (default: 'latest')

        Returns:
            Block data dictionary with fields like number, hash, timestamp, transactions, etc.

        Raises:
            InvalidBlockError: If block identifier is invalid
            AllProvidersFailedError: If all providers fail
        """
        params = {"block_identifier": block_identifier}
        return await self.request_handler.execute("get_block", params)

    async def get_transaction(self, tx_hash: str) -> dict[str, Any] | None:
        """
        Get transaction data.

        Args:
            tx_hash: Transaction hash (hex string)

        Returns:
            Transaction data dictionary or None if not found

        Raises:
            AllProvidersFailedError: If all providers fail
        """
        params = {"tx_hash": tx_hash}
        return await self.request_handler.execute("get_transaction", params)

    async def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any] | None:
        """
        Get transaction receipt.

        Args:
            tx_hash: Transaction hash (hex string)

        Returns:
            Transaction receipt dictionary or None if transaction not mined yet

        Raises:
            AllProvidersFailedError: If all providers fail
        """
        params = {"tx_hash": tx_hash}
        return await self.request_handler.execute("get_transaction_receipt", params)

    async def call_contract(
        self,
        address: str,
        abi: list[dict[str, Any]],
        method: str,
        args: list[Any] | None = None,
        block: str | int = "latest",
    ) -> Any:
        """
        Call a contract read method (view/pure function).

        Args:
            address: Contract address (hex string)
            abi: Contract ABI (list of function/event definitions)
            method: Method name to call
            args: Method arguments (default: [])
            block: Block at which to execute the call (default: 'latest')

        Returns:
            Decoded return value(s) from the contract method

        Raises:
            InvalidAddressError: If address format is invalid
            ContractCallError: If contract call fails
            AllProvidersFailedError: If all providers fail
        """
        if args is None:
            args = []

        params = {
            "address": address,
            "abi": abi,
            "method": method,
            "args": args,
            "block": block,
        }
        return await self.request_handler.execute("call_contract", params)

    async def get_logs(
        self,
        address: str | list[str] | None = None,
        topics: list[str | list[str] | None] | None = None,
        from_block: int | str = 0,
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """
        Get event logs matching filter criteria.

        Args:
            address: Contract address(es) to filter by (default: all addresses)
            topics: Event topics to filter by (default: all topics)
            from_block: Starting block number or 'earliest' (default: 0)
            to_block: Ending block number or 'latest' (default: 'latest')

        Returns:
            List of log entries

        Raises:
            ProviderError: If block range is too large
            AllProvidersFailedError: If all providers fail
        """
        params = {
            "address": address,
            "topics": topics,
            "from_block": from_block,
            "to_block": to_block,
        }
        return await self.request_handler.execute("get_logs", params)

    async def get_block_number(self) -> int:
        """
        Get the current block number.

        Returns:
            Current block number

        Raises:
            AllProvidersFailedError: If all providers fail
        """
        params: dict[str, Any] = {}
        return await self.request_handler.execute("get_block_number", params, use_cache=False)

    def get_provider_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get health and performance statistics for all providers.

        Returns:
            Dictionary mapping provider names to their statistics
        """
        return self.provider_manager.get_provider_stats()

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache hit rate, size, and other metrics
        """
        return self.cache_manager.get_stats()

    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache_manager.clear()

    async def __aenter__(self) -> ChainReader:
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        # In Phase 1, no cleanup needed
        # In future phases, close database connections, etc.
        pass
