"""Tests for custom exceptions"""

from chainreader.exceptions import (
    AllProvidersFailedError,
    CacheError,
    ChainReaderError,
    ContractCallError,
    InvalidAddressError,
    InvalidBlockError,
    ProviderError,
    RateLimitError,
)


def test_chain_reader_error():
    """Test base ChainReaderError"""
    error = ChainReaderError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_provider_error():
    """Test ProviderError with provider name"""
    error = ProviderError("infura", "Connection failed")
    assert "infura" in str(error)
    assert "Connection failed" in str(error)
    assert error.provider_name == "infura"


def test_provider_error_with_original():
    """Test ProviderError with original exception"""
    original = ValueError("Original error")
    error = ProviderError("alchemy", "Wrapper message", original)
    assert error.original_error == original
    assert error.provider_name == "alchemy"


def test_all_providers_failed_error():
    """Test AllProvidersFailedError"""
    error = AllProvidersFailedError()
    assert "All RPC providers have failed" in str(error)

    error = AllProvidersFailedError("Custom message")
    assert "Custom message" in str(error)


def test_rate_limit_error():
    """Test RateLimitError"""
    error = RateLimitError("provider1")
    assert "provider1" in str(error)
    assert "Rate limit exceeded" in str(error)
    assert error.retry_after is None


def test_rate_limit_error_with_retry_after():
    """Test RateLimitError with retry_after"""
    error = RateLimitError("provider2", retry_after=30.5)
    assert error.retry_after == 30.5
    assert "30.5" in str(error)
    assert "retry after" in str(error)


def test_cache_error():
    """Test CacheError"""
    error = CacheError("Cache write failed")
    assert "Cache write failed" in str(error)


def test_invalid_address_error():
    """Test InvalidAddressError"""
    error = InvalidAddressError("0xInvalid")
    assert "0xInvalid" in str(error)
    assert error.address == "0xInvalid"


def test_invalid_block_error():
    """Test InvalidBlockError with string"""
    error = InvalidBlockError("invalid")
    assert "invalid" in str(error)
    assert error.block_identifier == "invalid"


def test_invalid_block_error_with_int():
    """Test InvalidBlockError with integer"""
    error = InvalidBlockError(12345)
    assert "12345" in str(error)
    assert error.block_identifier == 12345


def test_contract_call_error():
    """Test ContractCallError"""
    error = ContractCallError("0x123", "balanceOf", "Execution reverted")
    assert "0x123" in str(error)
    assert "balanceOf" in str(error)
    assert "Execution reverted" in str(error)
    assert error.address == "0x123"
    assert error.method == "balanceOf"


def test_exception_inheritance():
    """Test that all exceptions inherit from ChainReaderError"""
    assert issubclass(ProviderError, ChainReaderError)
    assert issubclass(AllProvidersFailedError, ChainReaderError)
    assert issubclass(RateLimitError, ProviderError)
    assert issubclass(CacheError, ChainReaderError)
    assert issubclass(InvalidAddressError, ChainReaderError)
    assert issubclass(InvalidBlockError, ChainReaderError)
    assert issubclass(ContractCallError, ChainReaderError)
