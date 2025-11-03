"""Pytest configuration and shared fixtures"""

from typing import Union

import pytest


@pytest.fixture
def sample_providers() -> list[dict[str, Union[str, int]]]:
    """Sample provider configurations for testing"""
    return [
        {"name": "provider1", "url": "https://rpc1.example.com", "priority": 1},
        {"name": "provider2", "url": "https://rpc2.example.com", "priority": 2},
        {"name": "provider3", "url": "https://rpc3.example.com", "priority": 3},
    ]


@pytest.fixture
def sample_erc20_abi() -> list[dict]:
    """Sample ERC20 ABI for testing contract calls"""
    return [
        {
            "constant": True,
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"},
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function",
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "from", "type": "address"},
                {"indexed": True, "name": "to", "type": "address"},
                {"indexed": False, "name": "value", "type": "uint256"},
            ],
            "name": "Transfer",
            "type": "event",
        },
    ]


@pytest.fixture
def sample_address() -> str:
    """Sample Ethereum address"""
    return "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


@pytest.fixture
def sample_tx_hash() -> str:
    """Sample transaction hash"""
    return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
