# Changelog

All notable changes to ChainReader will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-11-03

### Added
- **Multi-provider RPC management** with automatic failover
  - Configure multiple RPC endpoints with priority levels
  - Automatic provider switching on failures
  - Health tracking and metrics for each provider
  - Round-robin selection within same priority level
  - Automatic recovery after cooldown period

- **Intelligent caching system**
  - In-memory cache with configurable TTL strategies
  - Permanent caching for immutable data (historical blocks, transaction receipts)
  - Time-based TTL for recent/latest data
  - Smart cache key generation
  - Cache statistics and monitoring
  - Automatic cache eviction when size limit reached

- **Core blockchain operations**
  - `get_balance()` - Get account balance
  - `get_block()` - Get block data
  - `get_transaction()` - Get transaction details
  - `get_transaction_receipt()` - Get transaction receipt
  - `call_contract()` - Call contract read methods with ABI encoding/decoding
  - `get_logs()` - Fetch event logs with filtering
  - `get_block_number()` - Get current block number

- **Robust error handling**
  - Custom exception hierarchy
  - Retry logic with exponential backoff
  - Provider-specific error tracking
  - Graceful degradation

- **Developer experience**
  - Full async/await support
  - Comprehensive type hints with Python 3.9+ compatibility
  - Context manager support for resource cleanup
  - Detailed logging
  - Provider and cache statistics endpoints

- **Testing and quality**
  - 61 unit and integration tests
  - 62% code coverage (97% on provider manager, 93% on cache manager, 100% on exceptions)
  - Pre-commit hooks (Black, Ruff, MyPy, pytest)
  - GitHub Actions CI/CD pipeline
  - Multi-Python version testing (3.9, 3.10, 3.11, 3.12)
  - Codecov integration

- **Documentation**
  - Comprehensive README with examples
  - Contributing guidelines
  - API documentation with docstrings
  - Example scripts for basic and multi-provider usage

### Technical Details
- Python 3.9+ support using `from __future__ import annotations`
- EVM-compatible (Ethereum, Polygon, BSC, Arbitrum, etc.)
- MIT License

### Known Limitations
- In-memory cache only (SQLite/Redis planned for Phase 2)
- No request batching (planned for Phase 3)
- No request deduplication (planned for Phase 3)
- No adaptive rate limiting (planned for Phase 3)

[0.1.0]: https://github.com/TickTockBent/chainreader/releases/tag/v0.1.0
