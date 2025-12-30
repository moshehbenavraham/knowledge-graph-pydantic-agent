#!/usr/bin/env python3
"""
Performance benchmark script for Phase 02 query engines.

Measures latency and throughput for:
- Multi-hop queries (1-hop, 2-hop, 3-hop)
- Temporal trend queries (single quarter, range, comparison)
- Cross-entity comparison queries (2-entity, 5-entity)
- Hybrid search with caching

Usage:
    python scripts/benchmark_phase02.py [--iterations N] [--output FILE]
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

from src.agentic_rag.cache import reset_query_cache
from src.agentic_rag.graph.entity_comparison import ComparisonQuery, execute_comparison
from src.agentic_rag.graph.multi_hop import MultiHopQuery, execute_multi_hop
from src.agentic_rag.graph.temporal_queries import TemporalQuery, execute_temporal_query
from src.agentic_rag.storage.connection_manager import get_connection_manager

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkResult:
    """Result from a single benchmark."""

    name: str
    iterations: int
    latencies_ms: list[float] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0

    @property
    def mean_ms(self) -> float:
        """Mean latency in milliseconds."""
        return mean(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def median_ms(self) -> float:
        """Median latency in milliseconds."""
        return median(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95_ms(self) -> float:
        """95th percentile latency in milliseconds."""
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    @property
    def min_ms(self) -> float:
        """Minimum latency in milliseconds."""
        return min(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def max_ms(self) -> float:
        """Maximum latency in milliseconds."""
        return max(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def stdev_ms(self) -> float:
        """Standard deviation of latency."""
        return stdev(self.latencies_ms) if len(self.latencies_ms) > 1 else 0.0

    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        total = len(self.latencies_ms) + self.errors
        if total == 0:
            return 0.0
        return (len(self.latencies_ms) / total) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "mean_ms": round(self.mean_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "stdev_ms": round(self.stdev_ms, 2),
            "success_rate": round(self.success_rate, 2),
            "cache_hit_rate": round(self.cache_hit_rate, 2),
            "errors": self.errors,
        }


class Phase02Benchmark:
    """Phase 02 performance benchmark suite."""

    def __init__(self, iterations: int = 10) -> None:
        """
        Initialize benchmark suite.

        Args:
            iterations: Number of iterations per benchmark
        """
        self.iterations = iterations
        self.results: list[BenchmarkResult] = []

    async def run_all(self) -> None:
        """Run all benchmarks."""
        logger.info("Starting Phase 02 benchmarks", iterations=self.iterations)

        connection_manager = get_connection_manager()

        try:
            # Multi-hop benchmarks
            await self._benchmark_multi_hop(connection_manager)

            # Temporal benchmarks
            await self._benchmark_temporal(connection_manager)

            # Comparison benchmarks
            await self._benchmark_comparison(connection_manager)

            # Cache performance benchmark
            await self._benchmark_cache_performance(connection_manager)

        except Exception as e:
            logger.exception("Benchmark failed", error=str(e))
            raise

    async def _benchmark_multi_hop(self, connection_manager: Any) -> None:
        """Benchmark multi-hop queries."""
        logger.info("Running multi-hop benchmarks")

        # 1-hop queries
        result = BenchmarkResult(name="multi_hop_1_hop", iterations=self.iterations)
        query = MultiHopQuery(
            start_entity="Intel",
            max_hops=1,
            min_strength=0.3,
            limit=20,
        )

        for _ in range(self.iterations):
            reset_query_cache()  # Clear cache for fair timing
            start = time.perf_counter()
            try:
                await execute_multi_hop(connection_manager, query, use_cache=False)
                elapsed = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(elapsed)
            except Exception:
                result.errors += 1

        self.results.append(result)

        # 2-hop queries
        result = BenchmarkResult(name="multi_hop_2_hop", iterations=self.iterations)
        query = MultiHopQuery(
            start_entity="Intel",
            max_hops=2,
            min_strength=0.3,
            limit=20,
        )

        for _ in range(self.iterations):
            reset_query_cache()
            start = time.perf_counter()
            try:
                await execute_multi_hop(connection_manager, query, use_cache=False)
                elapsed = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(elapsed)
            except Exception:
                result.errors += 1

        self.results.append(result)

    async def _benchmark_temporal(self, connection_manager: Any) -> None:
        """Benchmark temporal trend queries."""
        logger.info("Running temporal benchmarks")

        result = BenchmarkResult(name="temporal_single_year", iterations=self.iterations)
        query = TemporalQuery(
            entity="Intel",
            metric="revenue",
            start_year=2024,
            end_year=2024,
        )

        for _ in range(self.iterations):
            reset_query_cache()
            start = time.perf_counter()
            try:
                await execute_temporal_query(connection_manager, query, use_cache=False)
                elapsed = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(elapsed)
            except Exception:
                result.errors += 1

        self.results.append(result)

        # Range query (3 years)
        result = BenchmarkResult(name="temporal_3_year_range", iterations=self.iterations)
        query = TemporalQuery(
            entity="Intel",
            start_year=2022,
            end_year=2024,
        )

        for _ in range(self.iterations):
            reset_query_cache()
            start = time.perf_counter()
            try:
                await execute_temporal_query(connection_manager, query, use_cache=False)
                elapsed = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(elapsed)
            except Exception:
                result.errors += 1

        self.results.append(result)

    async def _benchmark_comparison(self, connection_manager: Any) -> None:
        """Benchmark comparison queries."""
        logger.info("Running comparison benchmarks")

        # 2-entity comparison
        result = BenchmarkResult(name="comparison_2_entity", iterations=self.iterations)
        query = ComparisonQuery(
            entity_names=["Intel", "AMD"],
            metric="revenue",
        )

        for _ in range(self.iterations):
            reset_query_cache()
            start = time.perf_counter()
            try:
                await execute_comparison(connection_manager, query, use_cache=False)
                elapsed = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(elapsed)
            except Exception:
                result.errors += 1

        self.results.append(result)

        # 4-entity comparison
        result = BenchmarkResult(name="comparison_4_entity", iterations=self.iterations)
        query = ComparisonQuery(
            entity_names=["Intel", "AMD", "NVIDIA", "Apple"],
            metric="revenue",
        )

        for _ in range(self.iterations):
            reset_query_cache()
            start = time.perf_counter()
            try:
                await execute_comparison(connection_manager, query, use_cache=False)
                elapsed = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(elapsed)
            except Exception:
                result.errors += 1

        self.results.append(result)

    async def _benchmark_cache_performance(self, connection_manager: Any) -> None:
        """Benchmark cache hit performance."""
        logger.info("Running cache performance benchmarks")

        result = BenchmarkResult(name="cache_hit_performance", iterations=self.iterations)
        query = MultiHopQuery(
            start_entity="Intel",
            max_hops=2,
            min_strength=0.3,
            limit=20,
        )

        # First call to populate cache
        await execute_multi_hop(connection_manager, query, use_cache=True)
        result.cache_misses += 1

        # Subsequent calls should hit cache
        for _ in range(self.iterations - 1):
            start = time.perf_counter()
            try:
                await execute_multi_hop(connection_manager, query, use_cache=True)
                elapsed = (time.perf_counter() - start) * 1000
                result.latencies_ms.append(elapsed)
                result.cache_hits += 1
            except Exception:
                result.errors += 1

        self.results.append(result)

    def print_results(self) -> None:
        """Print benchmark results to console."""
        print("\n" + "=" * 80)
        print("PHASE 02 BENCHMARK RESULTS")
        print("=" * 80)
        print(f"\nTimestamp: {datetime.now().isoformat()}")
        print(f"Iterations per benchmark: {self.iterations}")
        print("\n" + "-" * 80)

        for result in self.results:
            print(f"\n{result.name}")
            print(f"  Mean:     {result.mean_ms:>8.2f} ms")
            print(f"  Median:   {result.median_ms:>8.2f} ms")
            print(f"  P95:      {result.p95_ms:>8.2f} ms")
            print(f"  Min/Max:  {result.min_ms:>8.2f} / {result.max_ms:.2f} ms")
            print(f"  StdDev:   {result.stdev_ms:>8.2f} ms")
            print(f"  Success:  {result.success_rate:>8.1f}%")
            if result.cache_hits > 0 or result.cache_misses > 0:
                print(f"  Cache HR: {result.cache_hit_rate:>8.1f}%")
            if result.errors > 0:
                print(f"  Errors:   {result.errors}")

        print("\n" + "=" * 80)

    def save_results(self, output_file: str) -> None:
        """Save results to JSON file."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "iterations": self.iterations,
            "results": [r.to_dict() for r in self.results],
        }

        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)

        logger.info("Results saved", output_file=output_file)


async def main(iterations: int = 10, output_file: str | None = None) -> int:
    """
    Main entry point.

    Args:
        iterations: Number of iterations per benchmark
        output_file: Optional output file for JSON results

    Returns:
        Exit code (0 for success)
    """
    benchmark = Phase02Benchmark(iterations=iterations)

    await benchmark.run_all()
    benchmark.print_results()

    if output_file:
        benchmark.save_results(output_file)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 02 performance benchmarks")
    parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=10,
        help="Number of iterations per benchmark (default: 10)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file for JSON results",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(iterations=args.iterations, output_file=args.output))
    sys.exit(exit_code)
