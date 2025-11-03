"""Chain Client for EVM blockchain interactions using Web3.py"""

from __future__ import annotations

import logging
from typing import Any

from web3 import AsyncWeb3
from web3.exceptions import Web3Exception
from web3.providers import AsyncHTTPProvider
from web3.types import BlockIdentifier, FilterParams

from chainreader.exceptions import (
    ContractCallError,
    InvalidAddressError,
    InvalidBlockError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class ChainClient:
    """
    EVM-specific blockchain client for read operations.

    Handles:
    - Web3.py integration
    - ABI encoding/decoding
    - Event log parsing
    - Block/transaction data formatting
    """

    def __init__(self, provider_url: str, chain_id: int, request_timeout: int = 30):
        """
        Initialize the chain client.

        Args:
            provider_url: RPC endpoint URL
            chain_id: Network chain ID
            request_timeout: Request timeout in seconds
        """
        self.provider_url = provider_url
        self.chain_id = chain_id
        self.request_timeout = request_timeout

        # Initialize Web3 with async HTTP provider
        self.w3 = AsyncWeb3(
            AsyncHTTPProvider(
                provider_url,
                request_kwargs={"timeout": request_timeout},
            )
        )

        logger.debug(f"Initialized ChainClient for chain_id={chain_id}, url={provider_url}")

    async def get_balance(self, address: str, block: BlockIdentifier = "latest") -> int:
        """
        Get the balance of an address in wei.

        Args:
            address: Ethereum address
            block: Block number, hash, or 'latest'/'earliest'

        Returns:
            Balance in wei

        Raises:
            InvalidAddressError: If address is invalid
            ProviderError: If RPC call fails
        """
        try:
            checksum_address = self._normalize_address(address)
            balance = await self.w3.eth.get_balance(checksum_address, block)
            return int(balance)
        except ValueError as e:
            raise InvalidAddressError(address) from e
        except Web3Exception as e:
            raise ProviderError(self.provider_url, f"get_balance failed: {e}", e) from e

    async def get_block(self, block_identifier: BlockIdentifier) -> dict[str, Any]:
        """
        Get block data.

        Args:
            block_identifier: Block number, hash, or 'latest'/'earliest'

        Returns:
            Block data dictionary

        Raises:
            InvalidBlockError: If block identifier is invalid
            ProviderError: If RPC call fails
        """
        try:
            block = await self.w3.eth.get_block(block_identifier, full_transactions=False)
            if block is None:
                raise InvalidBlockError(block_identifier)
            # Convert AttributeDict to regular dict
            return dict(block)
        except ValueError as e:
            raise InvalidBlockError(block_identifier) from e
        except Web3Exception as e:
            raise ProviderError(self.provider_url, f"get_block failed: {e}", e) from e

    async def get_transaction(self, tx_hash: str) -> dict[str, Any] | None:
        """
        Get transaction data.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction data dictionary or None if not found

        Raises:
            ProviderError: If RPC call fails
        """
        try:
            tx = await self.w3.eth.get_transaction(tx_hash)
            if tx is None:
                return None
            return dict(tx)
        except Web3Exception as e:
            raise ProviderError(self.provider_url, f"get_transaction failed: {e}", e) from e

    async def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any] | None:
        """
        Get transaction receipt.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction receipt dictionary or None if not found

        Raises:
            ProviderError: If RPC call fails
        """
        try:
            receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
            if receipt is None:
                return None
            return dict(receipt)
        except Web3Exception as e:
            raise ProviderError(self.provider_url, f"get_transaction_receipt failed: {e}", e) from e

    async def call_contract(
        self,
        address: str,
        abi: list[dict[str, Any]],
        method: str,
        args: list[Any] | None = None,
        block: BlockIdentifier = "latest",
    ) -> Any:
        """
        Call a contract read method (view/pure function).

        Args:
            address: Contract address
            abi: Contract ABI
            method: Method name to call
            args: Method arguments
            block: Block at which to execute the call

        Returns:
            Decoded return value(s) from the contract method

        Raises:
            InvalidAddressError: If address is invalid
            ContractCallError: If contract call fails
            ProviderError: If RPC call fails
        """
        if args is None:
            args = []

        try:
            checksum_address = self._normalize_address(address)
            contract = self.w3.eth.contract(address=checksum_address, abi=abi)

            # Get the contract function
            if not hasattr(contract.functions, method):
                raise ContractCallError(address, method, f"Method '{method}' not found in ABI")

            contract_function = getattr(contract.functions, method)

            # Call the function
            result = await contract_function(*args).call(block_identifier=block)
            return result

        except ValueError as e:
            if "invalid address" in str(e).lower():
                raise InvalidAddressError(address) from e
            raise ContractCallError(address, method, str(e)) from e
        except Web3Exception as e:
            raise ProviderError(self.provider_url, f"call_contract failed: {e}", e) from e
        except Exception as e:
            raise ContractCallError(address, method, str(e)) from e

    async def get_logs(
        self,
        address: str | list[str] | None = None,
        topics: list[str | list[str] | None] | None = None,
        from_block: int | str = 0,
        to_block: int | str = "latest",
    ) -> list[dict[str, Any]]:
        """
        Get event logs matching the filter criteria.

        Args:
            address: Contract address(es) to filter by
            topics: Event topics to filter by
            from_block: Starting block number or 'earliest'
            to_block: Ending block number or 'latest'

        Returns:
            List of log entries

        Raises:
            ProviderError: If RPC call fails
        """
        try:
            # Build filter params
            filter_params: FilterParams = {
                "fromBlock": from_block,
                "toBlock": to_block,
            }

            if address is not None:
                if isinstance(address, list):
                    filter_params["address"] = [self._normalize_address(addr) for addr in address]
                else:
                    filter_params["address"] = self._normalize_address(address)

            if topics is not None:
                filter_params["topics"] = topics  # type: ignore

            logs = await self.w3.eth.get_logs(filter_params)
            return [dict(log) for log in logs]

        except ValueError as e:
            if "too many results" in str(e).lower() or "range too large" in str(e).lower():
                raise ProviderError(
                    self.provider_url,
                    f"Block range too large ({from_block} to {to_block}), " "try a smaller range",
                    e,
                ) from e
            raise ProviderError(self.provider_url, f"get_logs failed: {e}", e) from e
        except Web3Exception as e:
            raise ProviderError(self.provider_url, f"get_logs failed: {e}", e) from e

    async def get_block_number(self) -> int:
        """
        Get the latest block number.

        Returns:
            Current block number

        Raises:
            ProviderError: If RPC call fails
        """
        try:
            block_number = await self.w3.eth.block_number
            return int(block_number)
        except Web3Exception as e:
            raise ProviderError(self.provider_url, f"get_block_number failed: {e}", e) from e

    async def is_connected(self) -> bool:
        """
        Check if connected to the provider.

        Returns:
            True if connected, False otherwise
        """
        try:
            return await self.w3.is_connected()
        except Exception:
            return False

    def _normalize_address(self, address: str) -> str:
        """
        Normalize and validate an Ethereum address.

        Args:
            address: Ethereum address

        Returns:
            Checksummed address

        Raises:
            InvalidAddressError: If address is invalid
        """
        try:
            return self.w3.to_checksum_address(address)
        except ValueError as e:
            raise InvalidAddressError(address) from e
