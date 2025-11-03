# ChainReader

[![CI](https://github.com/yourusername/chainreader/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/chainreader/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yourusername/chainreader/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/chainreader)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**EVM-Compatible Blockchain Data Reader with Intelligent RPC Provider Management**

ChainReader is a Python library for reliably fetching on-chain data from EVM-compatible blockchains with automatic failover, smart caching, and provider health tracking.

## Features

### Phase 1 (Current) ✅

- **Multi-Provider Management**: Configure multiple RPC endpoints with automatic failover
- **Intelligent Caching**: In-memory caching with smart TTL for different data types
- **Provider Health Tracking**: Automatic detection and recovery of failed providers
- **Retry Logic**: Exponential backoff with configurable retry attempts
- **EVM Compatible**: Works with Ethereum, Polygon, BSC, Arbitrum, and any EVM chain

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from chainreader import ChainReader

async def main():
    # Initialize with multiple providers
    reader = ChainReader(
        chain_id=137,  # Polygon mainnet
        providers=[
            {'name': 'infura', 'url': 'https://polygon-mainnet.infura.io/v3/YOUR_KEY'},
            {'name': 'alchemy', 'url': 'https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY'},
            {'name': 'public', 'url': 'https://polygon-rpc.com'}
        ]
    )

    async with reader:
        # Get account balance
        balance = await reader.get_balance('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb')
        print(f"Balance: {balance / 10**18} MATIC")

        # Get latest block
        block = await reader.get_block('latest')
        print(f"Block number: {block['number']}")

        # Call contract method
        result = await reader.call_contract(
            address='0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',  # USDC on Polygon
            abi=usdc_abi,
            method='balanceOf',
            args=['0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb']
        )
        print(f"USDC Balance: {result / 10**6}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Usage

### Initialize ChainReader

```python
from chainreader import ChainReader

reader = ChainReader(
    chain_id=137,  # Network chain ID
    providers=[
        {'name': 'provider1', 'url': 'https://rpc1.example.com', 'priority': 1},
        {'name': 'provider2', 'url': 'https://rpc2.example.com', 'priority': 2},
    ],

    # Cache configuration
    cache_ttl_blocks=12,      # TTL for recent data (seconds)
    cache_ttl_latest=5,       # TTL for 'latest' queries (seconds)
    max_cache_size=10000,     # Maximum cache entries

    # Retry configuration
    max_retries=3,            # Max retry attempts
    retry_backoff_factor=2.0, # Exponential backoff factor

    # Provider management
    failover_threshold=3,     # Failures before marking unhealthy
    health_check_cooldown=300,# Seconds before re-enabling provider

    # Request settings
    request_timeout=30,       # RPC request timeout (seconds)
    log_level='INFO'          # Logging level
)
```

### Available Methods

#### Get Balance
```python
balance = await reader.get_balance(
    address='0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb',
    block='latest'  # or block number
)
```

#### Get Block
```python
block = await reader.get_block('latest')
# or
block = await reader.get_block(12345678)
# or
block = await reader.get_block('0xabcdef...')
```

#### Get Transaction
```python
tx = await reader.get_transaction('0x1234...')
```

#### Get Transaction Receipt
```python
receipt = await reader.get_transaction_receipt('0x1234...')
```

#### Call Contract Method
```python
result = await reader.call_contract(
    address='0x...',
    abi=[...],
    method='balanceOf',
    args=['0x...'],
    block='latest'
)
```

#### Get Event Logs
```python
logs = await reader.get_logs(
    address='0x...',
    topics=['0x...'],  # Event signature
    from_block=1000000,
    to_block=1001000
)
```

#### Get Current Block Number
```python
block_number = await reader.get_block_number()
```

### Monitoring

#### Provider Statistics
```python
stats = reader.get_provider_stats()
# Returns:
# {
#     'provider1': {
#         'is_healthy': True,
#         'success_count': 42,
#         'failure_count': 1,
#         'success_rate': 0.976,
#         'average_latency': 0.234,
#         ...
#     },
#     ...
# }
```

#### Cache Statistics
```python
stats = reader.get_cache_stats()
# Returns:
# {
#     'hits': 150,
#     'misses': 50,
#     'hit_rate': 0.75,
#     'size': 234
# }
```

## Caching Strategy

ChainReader automatically applies intelligent caching based on data type:

- **Permanent**: Transaction receipts, historical blocks (>12 blocks old), historical contract calls
- **Short TTL (5s)**: Latest block queries, current state
- **Medium TTL (12s)**: Recent blocks, recent contract calls
- **No cache**: Pending transactions, current mempool

## Provider Failover

ChainReader automatically handles provider failures:

1. **Health Tracking**: Each provider's success/failure rate is monitored
2. **Automatic Failover**: Failed requests automatically retry with the next provider
3. **Priority-based Selection**: Providers are tried in priority order (lower number = higher priority)
4. **Auto Recovery**: Failed providers are re-enabled after a cooldown period

## Examples

See the [examples](examples/) directory for complete examples:

- [basic_usage.py](examples/basic_usage.py) - Basic operations with single provider
- [multi_provider.py](examples/multi_provider.py) - Multi-provider setup with failover demonstration

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/chainreader.git
cd chainreader

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chainreader --cov-report=html

# Run specific test file
pytest tests/test_provider_manager.py
```

### Code Quality

```bash
# Format code
black chainreader tests

# Lint code
ruff check chainreader tests

# Type checking
mypy chainreader
```

## Supported Chains

ChainReader works with any EVM-compatible blockchain:

- Ethereum (chain_id: 1)
- Polygon (chain_id: 137)
- BSC (chain_id: 56)
- Arbitrum (chain_id: 42161)
- Optimism (chain_id: 10)
- Avalanche C-Chain (chain_id: 43114)
- And many more...

## Error Handling

ChainReader provides specific exceptions for different error cases:

```python
from chainreader import (
    ChainReaderError,           # Base exception
    AllProvidersFailedError,    # All providers failed
    ProviderError,              # Single provider error
    RateLimitError,             # Rate limit exceeded
    InvalidAddressError,        # Invalid address format
    ContractCallError,          # Contract call failed
)

try:
    balance = await reader.get_balance('0x...')
except InvalidAddressError:
    print("Invalid address format")
except AllProvidersFailedError:
    print("All RPC providers are down")
except ChainReaderError as e:
    print(f"ChainReader error: {e}")
```

## Roadmap

### Phase 2 (Planned)
- SQLite cache backend for persistent caching
- Redis cache backend for shared caching
- Advanced cache warming and prefetching

### Phase 3 (Planned)
- Request batching for eth_call
- Request deduplication
- Adaptive rate limiting
- Priority queue for requests

### Phase 4 (Planned)
- Comprehensive testing (>80% coverage)
- Performance benchmarks
- Production-ready documentation

### Phase 5 (Planned)
- FastAPI service layer
- WebSocket event subscriptions
- Admin dashboard
- Docker deployment

## Contributing

Contributions are welcome! Areas where we'd love help:

- Additional chain support and testing
- New cache backends
- Performance optimizations
- Documentation improvements
- Bug fixes

## License

MIT License - Free for commercial and personal use.

## Acknowledgments

Built for use in:
- [Candlemark](https://github.com/yourusername/candlemark) - Prediction market dApp
- [Dodona Oracles](https://github.com/yourusername/dodona) - Trading bot infrastructure

---

**Note**: This is a Phase 1 release. Features like SQLite/Redis caching, request batching, and rate limiting are planned for future releases.
