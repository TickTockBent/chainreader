"""
Basic ChainReader usage example.

This example demonstrates:
- Initializing ChainReader with a single provider
- Fetching account balance
- Fetching latest block
- Calling a contract read method
"""

import asyncio
import os

from chainreader import ChainReader

# Sample ERC20 ABI (just the balanceOf function)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
]


async def main() -> None:
    # Get RPC URL from environment (or use a public endpoint)
    rpc_url = os.getenv("RPC_URL", "https://polygon-rpc.com")

    # Initialize ChainReader with a single provider
    reader = ChainReader(
        chain_id=137,  # Polygon mainnet
        providers=[
            {"name": "polygon", "url": rpc_url},
        ],
        log_level="INFO",
    )

    async with reader:
        print("=== ChainReader Basic Usage Example ===\n")

        # Example 1: Get account balance
        address = "0x0000000000000000000000000000000000001010"  # MATIC token on Polygon
        print(f"Fetching balance for {address}...")
        balance = await reader.get_balance(address)
        print(f"Balance: {balance / 10**18:.4f} MATIC\n")

        # Example 2: Get latest block
        print("Fetching latest block...")
        block = await reader.get_block("latest")
        print(f"Block number: {block['number']}")
        print(f"Block hash: {block['hash'].hex()}")
        print(f"Timestamp: {block['timestamp']}")
        print(f"Transactions: {len(block['transactions'])}\n")

        # Example 3: Get specific block number
        print("Fetching current block number...")
        block_number = await reader.get_block_number()
        print(f"Current block: {block_number}\n")

        # Example 4: Call contract method (USDC balance on Polygon)
        usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
        holder_address = "0x0000000000000000000000000000000000001010"

        print(f"Fetching USDC balance for {holder_address}...")
        try:
            usdc_balance = await reader.call_contract(
                address=usdc_address,
                abi=ERC20_ABI,
                method="balanceOf",
                args=[holder_address],
            )
            print(f"USDC Balance: {usdc_balance / 10**6:.2f} USDC\n")
        except Exception as e:
            print(f"Error calling contract: {e}\n")

        # Example 5: Cache statistics
        print("=== Cache Statistics ===")
        cache_stats = reader.get_cache_stats()
        print(f"Cache hits: {cache_stats['hits']}")
        print(f"Cache misses: {cache_stats['misses']}")
        print(f"Hit rate: {cache_stats['hit_rate']:.2%}")
        print(f"Cache size: {cache_stats['size']} entries\n")

        # Example 6: Provider statistics
        print("=== Provider Statistics ===")
        provider_stats = reader.get_provider_stats()
        for name, stats in provider_stats.items():
            print(f"\nProvider: {name}")
            print(f"  Healthy: {stats['is_healthy']}")
            print(f"  Success count: {stats['success_count']}")
            print(f"  Failure count: {stats['failure_count']}")
            print(f"  Success rate: {stats['success_rate']:.2%}")
            if stats["average_latency"] > 0:
                print(f"  Average latency: {stats['average_latency']:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
