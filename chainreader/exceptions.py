"""Custom exceptions for ChainReader"""


class ChainReaderError(Exception):
    """Base exception for all ChainReader errors"""

    pass


class ProviderError(ChainReaderError):
    """Error from a specific RPC provider"""

    def __init__(self, provider_name: str, message: str, original_error: Exception | None = None):
        self.provider_name = provider_name
        self.original_error = original_error
        super().__init__(f"Provider '{provider_name}': {message}")


class AllProvidersFailedError(ChainReaderError):
    """All configured providers have failed"""

    def __init__(self, message: str = "All RPC providers have failed"):
        super().__init__(message)


class RateLimitError(ProviderError):
    """Rate limit exceeded on provider"""

    def __init__(self, provider_name: str, retry_after: float | None = None):
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(provider_name, msg)


class CacheError(ChainReaderError):
    """Error in cache operations"""

    pass


class InvalidAddressError(ChainReaderError):
    """Invalid Ethereum address format"""

    def __init__(self, address: str):
        self.address = address
        super().__init__(f"Invalid Ethereum address: {address}")


class InvalidBlockError(ChainReaderError):
    """Invalid block identifier"""

    def __init__(self, block_identifier: str | int):
        self.block_identifier = block_identifier
        super().__init__(f"Invalid block identifier: {block_identifier}")


class ContractCallError(ChainReaderError):
    """Error calling contract method"""

    def __init__(self, address: str, method: str, message: str):
        self.address = address
        self.method = method
        super().__init__(f"Contract call failed at {address}.{method}: {message}")
