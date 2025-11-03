"""
Multi-provider failover example.

This example demonstrates:
- Configuring multiple RPC providers
- Automatic provider failover
- Provider health tracking
- Cache benefits across retries
"""

import asyncio
import os

from chainreader import ChainReader


async def main() -> None:
    # Configure multiple providers with priority
    providers = [
        {
            "name": "infura",
            "url": os.getenv("INFURA_URL", "https://polygon-mainnet.infura.io/v3/YOUR_KEY"),
            "priority": 1,  # Highest priority
        },
        {
            "name": "alchemy",
            "url": os.getenv("ALCHEMY_URL", "https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY"),
            "priority": 2,
        },
        {
            "name": "public",
            "url": "https://polygon-rpc.com",
            "priority": 3,  # Lowest priority (fallback)
        },
    ]

    # Initialize with multiple providers and custom failover settings
    reader = ChainReader(
        chain_id=137,  # Polygon mainnet
        providers=providers,
        max_retries=5,  # Try up to 5 times
        failover_threshold=2,  # Mark provider unhealthy after 2 failures
        health_check_cooldown=60,  # Re-enable failed providers after 60 seconds
        log_level="INFO",
    )

    async with reader:
        print("=== ChainReader Multi-Provider Example ===\n")

        # Show initial provider status
        print("Initial provider status:")
        print_provider_stats(reader)

        # Make several requests to demonstrate failover
        print("\n=== Making Requests ===\n")

        test_address = "0x0000000000000000000000000000000000001010"

        for i in range(5):
            print(f"Request {i + 1}...")
            try:
                balance = await reader.get_balance(test_address)
                print(f"  Balance: {balance / 10**18:.4f} MATIC")

                # Show which provider was used
                stats = reader.get_provider_stats()
                active_providers = [
                    name
                    for name, stat in stats.items()
                    if stat["success_count"] > 0 and stat["is_healthy"]
                ]
                print(f"  Active providers: {', '.join(active_providers)}")

            except Exception as e:
                print(f"  Error: {e}")

            print()

        # Show final provider status
        print("\n=== Final Provider Status ===")
        print_provider_stats(reader)

        # Show cache benefits
        print("\n=== Cache Performance ===")
        cache_stats = reader.get_cache_stats()
        print(f"Total requests: {cache_stats['hits'] + cache_stats['misses']}")
        print(f"Cache hits: {cache_stats['hits']}")
        print(f"Cache misses: {cache_stats['misses']}")
        print(f"Hit rate: {cache_stats['hit_rate']:.2%}")
        print(f"\nBenefit: Saved {cache_stats['hits']} RPC calls!")


def print_provider_stats(reader: ChainReader) -> None:
    """Helper to print provider statistics"""
    stats = reader.get_provider_stats()

    for name, stat in stats.items():
        status = "✓" if stat["is_healthy"] else "✗"
        print(f"\n{status} {name} (priority {stat['priority']})")
        print(f"  URL: {stat['url']}")
        print(f"  Requests: {stat['request_count']}")
        print(f"  Successes: {stat['success_count']}")
        print(f"  Failures: {stat['failure_count']}")

        if stat["request_count"] > 0:
            print(f"  Success rate: {stat['success_rate']:.1%}")
            print(f"  Avg latency: {stat['average_latency']:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
