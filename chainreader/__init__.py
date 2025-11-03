"""
ChainReader: EVM-Compatible Blockchain Data Reader

A Python library for reliably fetching on-chain data from EVM-compatible
blockchains with intelligent RPC provider management, automatic failover,
smart caching, and rate limit handling.
"""

__version__ = "0.1.0"

from chainreader.chainreader import ChainReader
from chainreader.exceptions import (
    AllProvidersFailedError,
    CacheError,
    ChainReaderError,
    ProviderError,
    RateLimitError,
)

__all__ = [
    "ChainReader",
    "ChainReaderError",
    "AllProvidersFailedError",
    "ProviderError",
    "RateLimitError",
    "CacheError",
]
