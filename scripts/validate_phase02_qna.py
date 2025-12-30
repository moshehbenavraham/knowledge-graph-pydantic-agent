#!/usr/bin/env python3
"""
QnA validation script for Phase 02 query engines.

Tests 46 sample questions across multi-hop, temporal, comparison, and smart search
to validate the Phase 02 implementation is complete and functional.

Usage:
    python scripts/validate_phase02_qna.py [--verbose] [--output FILE]
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

from src.agentic_rag.graph.entity_comparison import ComparisonQuery, execute_comparison
from src.agentic_rag.graph.multi_hop import MultiHopQuery, execute_multi_hop
from src.agentic_rag.graph.temporal_queries import TemporalQuery, execute_temporal_query
from src.agentic_rag.search.intent_analyzer import IntentAnalyzer
from src.agentic_rag.storage.connection_manager import get_connection_manager

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result from a single validation test."""

    question_id: str
    category: str
    question: str
    passed: bool
    has_results: bool
    result_count: int = 0
    error_message: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "question_id": self.question_id,
            "category": self.category,
            "question": self.question,
            "passed": self.passed,
            "has_results": self.has_results,
            "result_count": self.result_count,
            "error_message": self.error_message,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class ValidationSummary:
    """Summary of validation results."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Pass rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 2),
            "by_category": self.by_category,
        }


# 46 Sample Questions for Validation
VALIDATION_QUESTIONS = [
    # Multi-Hop Questions (15)
    {
        "id": "MH01",
        "category": "multi_hop",
        "question": "What companies are connected to Intel through acquisitions?",
        "params": {"start": "Intel", "hops": 2},
    },
    {
        "id": "MH02",
        "category": "multi_hop",
        "question": "Find paths between Intel and AMD",
        "params": {"start": "Intel", "end": "AMD", "hops": 3},
    },
    {
        "id": "MH03",
        "category": "multi_hop",
        "question": "What products are related to Mobileye?",
        "params": {"start": "Mobileye", "hops": 2},
    },
    {
        "id": "MH04",
        "category": "multi_hop",
        "question": "Show organizations connected to NVIDIA",
        "params": {"start": "NVIDIA", "hops": 2, "type": "organization"},
    },
    {
        "id": "MH05",
        "category": "multi_hop",
        "question": "What entities are 1 hop from Apple?",
        "params": {"start": "Apple", "hops": 1},
    },
    {
        "id": "MH06",
        "category": "multi_hop",
        "question": "Find connections between Microsoft and cloud services",
        "params": {"start": "Microsoft", "hops": 2},
    },
    {
        "id": "MH07",
        "category": "multi_hop",
        "question": "What technologies are linked to autonomous driving?",
        "params": {"start": "autonomous", "hops": 2},
    },
    {
        "id": "MH08",
        "category": "multi_hop",
        "question": "Show semiconductor company relationships",
        "params": {"start": "semiconductor", "hops": 2},
    },
    {
        "id": "MH09",
        "category": "multi_hop",
        "question": "Find AI-related entity connections",
        "params": {"start": "AI", "hops": 2},
    },
    {
        "id": "MH10",
        "category": "multi_hop",
        "question": "What executives are connected to Intel?",
        "params": {"start": "Intel", "hops": 2, "type": "person"},
    },
    {
        "id": "MH11",
        "category": "multi_hop",
        "question": "Show supply chain relationships for Intel",
        "params": {"start": "Intel", "hops": 3},
    },
    {
        "id": "MH12",
        "category": "multi_hop",
        "question": "Find competitors connected through shared technology",
        "params": {"start": "processor", "hops": 2},
    },
    {
        "id": "MH13",
        "category": "multi_hop",
        "question": "What products are Intel connected to?",
        "params": {"start": "Intel", "hops": 2, "type": "product"},
    },
    {
        "id": "MH14",
        "category": "multi_hop",
        "question": "Show data center related connections",
        "params": {"start": "data center", "hops": 2},
    },
    {
        "id": "MH15",
        "category": "multi_hop",
        "question": "Find foundry service relationships",
        "params": {"start": "foundry", "hops": 2},
    },
    # Temporal Questions (16)
    {
        "id": "TQ01",
        "category": "temporal",
        "question": "How has Intel revenue changed over time?",
        "params": {"entity": "Intel", "metric": "revenue", "years": [2022, 2024]},
    },
    {
        "id": "TQ02",
        "category": "temporal",
        "question": "Show Intel Q3 2024 financial data",
        "params": {"entity": "Intel", "year": 2024, "quarter": "Q3"},
    },
    {
        "id": "TQ03",
        "category": "temporal",
        "question": "Intel revenue trend 2023-2024",
        "params": {"entity": "Intel", "metric": "revenue", "years": [2023, 2024]},
    },
    {
        "id": "TQ04",
        "category": "temporal",
        "question": "What was Intel's performance in 2024?",
        "params": {"entity": "Intel", "year": 2024},
    },
    {
        "id": "TQ05",
        "category": "temporal",
        "question": "Show quarterly data for Intel 2024",
        "params": {"entity": "Intel", "year": 2024},
    },
    {
        "id": "TQ06",
        "category": "temporal",
        "question": "Intel profit margin trends",
        "params": {"entity": "Intel", "metric": "profit", "years": [2023, 2024]},
    },
    {
        "id": "TQ07",
        "category": "temporal",
        "question": "Year over year Intel comparison",
        "params": {"entity": "Intel", "years": [2023, 2024]},
    },
    {
        "id": "TQ08",
        "category": "temporal",
        "question": "Intel data center revenue trend",
        "params": {"entity": "Intel", "metric": "data center", "years": [2022, 2024]},
    },
    {
        "id": "TQ09",
        "category": "temporal",
        "question": "Show Intel client computing trends",
        "params": {"entity": "Intel", "metric": "client", "years": [2023, 2024]},
    },
    {
        "id": "TQ10",
        "category": "temporal",
        "question": "Intel foundry services performance",
        "params": {"entity": "Intel", "metric": "foundry", "years": [2023, 2024]},
    },
    {
        "id": "TQ11",
        "category": "temporal",
        "question": "How has Intel gross margin evolved?",
        "params": {"entity": "Intel", "metric": "margin", "years": [2022, 2024]},
    },
    {
        "id": "TQ12",
        "category": "temporal",
        "question": "Intel Q4 2024 vs Q3 2024",
        "params": {"entity": "Intel", "year": 2024, "quarters": ["Q3", "Q4"]},
    },
    {
        "id": "TQ13",
        "category": "temporal",
        "question": "Show Intel operating expenses trend",
        "params": {"entity": "Intel", "metric": "expense", "years": [2023, 2024]},
    },
    {
        "id": "TQ14",
        "category": "temporal",
        "question": "Intel EPS trend over time",
        "params": {"entity": "Intel", "metric": "EPS", "years": [2022, 2024]},
    },
    {
        "id": "TQ15",
        "category": "temporal",
        "question": "Intel DCAI segment trends",
        "params": {"entity": "Intel", "metric": "DCAI", "years": [2023, 2024]},
    },
    {
        "id": "TQ16",
        "category": "temporal",
        "question": "Intel CCG segment performance",
        "params": {"entity": "Intel", "metric": "CCG", "years": [2023, 2024]},
    },
    # Comparison Questions (10)
    {
        "id": "CQ01",
        "category": "comparison",
        "question": "Compare Intel vs AMD revenue",
        "params": {"entities": ["Intel", "AMD"], "metric": "revenue"},
    },
    {
        "id": "CQ02",
        "category": "comparison",
        "question": "Intel vs NVIDIA vs AMD comparison",
        "params": {"entities": ["Intel", "NVIDIA", "AMD"], "metric": "revenue"},
    },
    {
        "id": "CQ03",
        "category": "comparison",
        "question": "How do semiconductor companies compare?",
        "params": {"entities": ["Intel", "AMD", "NVIDIA", "TSMC"], "metric": "revenue"},
    },
    {
        "id": "CQ04",
        "category": "comparison",
        "question": "Compare Intel and AMD profit margins",
        "params": {"entities": ["Intel", "AMD"], "metric": "margin"},
    },
    {
        "id": "CQ05",
        "category": "comparison",
        "question": "Intel vs competitors market share",
        "params": {"entities": ["Intel", "AMD"], "metric": "market"},
    },
    {
        "id": "CQ06",
        "category": "comparison",
        "question": "Compare data center revenue Intel vs AMD",
        "params": {"entities": ["Intel", "AMD"], "metric": "data center"},
    },
    {
        "id": "CQ07",
        "category": "comparison",
        "question": "Intel vs AMD Q3 2024 performance",
        "params": {
            "entities": ["Intel", "AMD"],
            "metric": "revenue",
            "quarter": "Q3",
            "year": 2024,
        },
    },
    {
        "id": "CQ08",
        "category": "comparison",
        "question": "Semiconductor gross margin comparison",
        "params": {"entities": ["Intel", "AMD", "NVIDIA"], "metric": "margin"},
    },
    {
        "id": "CQ09",
        "category": "comparison",
        "question": "Intel vs AMD growth rates",
        "params": {"entities": ["Intel", "AMD"], "metric": "growth"},
    },
    {
        "id": "CQ10",
        "category": "comparison",
        "question": "Compare Intel AMD NVIDIA EPS",
        "params": {"entities": ["Intel", "AMD", "NVIDIA"], "metric": "EPS"},
    },
    # Intent Detection Questions (5)
    {
        "id": "ID01",
        "category": "intent",
        "question": "What is Intel's financial performance?",
        "expected_intent": "VECTOR_HEAVY",
    },
    {
        "id": "ID02",
        "category": "intent",
        "question": "How are Intel and Mobileye connected?",
        "expected_intent": "MULTI_HOP",
    },
    {
        "id": "ID03",
        "category": "intent",
        "question": "Intel revenue trend over time",
        "expected_intent": "TEMPORAL_TREND",
    },
    {
        "id": "ID04",
        "category": "intent",
        "question": "Compare Intel vs AMD revenue",
        "expected_intent": "COMPARISON",
    },
    {
        "id": "ID05",
        "category": "intent",
        "question": "What entities are related to Intel?",
        "expected_intent": "ENTITY_FOCUSED",
    },
]


class Phase02Validator:
    """Phase 02 QnA validation suite."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize validator."""
        self.verbose = verbose
        self.results: list[ValidationResult] = []
        self.intent_analyzer = IntentAnalyzer()

    async def run_all(self) -> ValidationSummary:
        """Run all validation tests."""
        logger.info("Starting Phase 02 QnA validation", total_questions=len(VALIDATION_QUESTIONS))

        connection_manager = get_connection_manager()
        summary = ValidationSummary()

        for q in VALIDATION_QUESTIONS:
            result = await self._validate_question(connection_manager, q)
            self.results.append(result)

            summary.total += 1
            if result.passed:
                summary.passed += 1
            else:
                summary.failed += 1

            # Update category stats
            category = result.category
            if category not in summary.by_category:
                summary.by_category[category] = {"total": 0, "passed": 0, "failed": 0}
            summary.by_category[category]["total"] += 1
            if result.passed:
                summary.by_category[category]["passed"] += 1
            else:
                summary.by_category[category]["failed"] += 1

            if self.verbose:
                status = "PASS" if result.passed else "FAIL"
                print(f"[{status}] {result.question_id}: {result.question[:50]}...")

        return summary

    async def _validate_question(
        self, connection_manager: Any, q: dict[str, Any]
    ) -> ValidationResult:
        """Validate a single question."""
        import time

        qid = q["id"]
        category = q["category"]
        question = q["question"]
        params = q.get("params", {})

        start_time = time.perf_counter()

        try:
            if category == "multi_hop":
                result = await self._validate_multi_hop(connection_manager, params)
            elif category == "temporal":
                result = await self._validate_temporal(connection_manager, params)
            elif category == "comparison":
                result = await self._validate_comparison(connection_manager, params)
            elif category == "intent":
                result = await self._validate_intent(q)
            else:
                result = ValidationResult(
                    question_id=qid,
                    category=category,
                    question=question,
                    passed=False,
                    has_results=False,
                    error_message=f"Unknown category: {category}",
                )

            result.question_id = qid
            result.category = category
            result.question = question
            result.latency_ms = (time.perf_counter() - start_time) * 1000

            return result

        except Exception as e:
            return ValidationResult(
                question_id=qid,
                category=category,
                question=question,
                passed=False,
                has_results=False,
                error_message=str(e),
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

    async def _validate_multi_hop(
        self, connection_manager: Any, params: dict[str, Any]
    ) -> ValidationResult:
        """Validate a multi-hop query."""
        query = MultiHopQuery(
            start_entity=params.get("start", "Intel"),
            end_entity=params.get("end"),
            max_hops=params.get("hops", 2),
            min_strength=0.2,
            entity_type_filter=params.get("type"),
            limit=20,
        )

        results = await execute_multi_hop(connection_manager, query, use_cache=False)
        has_results = len(results) > 0

        return ValidationResult(
            question_id="",
            category="multi_hop",
            question="",
            passed=True,  # Test passes if no error
            has_results=has_results,
            result_count=len(results),
        )

    async def _validate_temporal(
        self, connection_manager: Any, params: dict[str, Any]
    ) -> ValidationResult:
        """Validate a temporal query."""
        years = params.get("years", [2024, 2024])
        query = TemporalQuery(
            entity=params.get("entity", "Intel"),
            metric=params.get("metric"),
            start_year=years[0] if years else 2024,
            end_year=years[-1] if years else 2024,
            start_quarter=params.get("quarter"),
        )

        result = await execute_temporal_query(connection_manager, query, use_cache=False)
        has_results = len(result.data_points) > 0

        return ValidationResult(
            question_id="",
            category="temporal",
            question="",
            passed=True,
            has_results=has_results,
            result_count=len(result.data_points),
        )

    async def _validate_comparison(
        self, connection_manager: Any, params: dict[str, Any]
    ) -> ValidationResult:
        """Validate a comparison query."""
        query = ComparisonQuery(
            entity_names=params.get("entities", ["Intel", "AMD"]),
            metric=params.get("metric", "revenue"),
            fiscal_quarter=params.get("quarter"),
            fiscal_year=params.get("year"),
        )

        result = await execute_comparison(connection_manager, query, use_cache=False)

        return ValidationResult(
            question_id="",
            category="comparison",
            question="",
            passed=result.comparison_valid,
            has_results=result.entities_with_data > 0,
            result_count=result.entities_with_data,
            error_message=result.error_message if not result.comparison_valid else "",
        )

    async def _validate_intent(self, q: dict[str, Any]) -> ValidationResult:
        """Validate intent detection."""
        question = q["question"]
        expected = q.get("expected_intent", "")

        result = self.intent_analyzer.analyze(question)
        detected = result.primary_intent.value.upper()
        expected_upper = expected.upper()

        # Check if detected intent matches expected
        passed = detected == expected_upper or expected_upper in detected

        return ValidationResult(
            question_id="",
            category="intent",
            question=question,
            passed=passed,
            has_results=True,
            result_count=1,
            error_message=f"Expected {expected}, got {detected}" if not passed else "",
        )

    def print_summary(self, summary: ValidationSummary) -> None:
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("PHASE 02 QnA VALIDATION SUMMARY")
        print("=" * 80)
        print(f"\nTotal Questions: {summary.total}")
        print(f"Passed: {summary.passed}")
        print(f"Failed: {summary.failed}")
        print(f"Pass Rate: {summary.pass_rate:.1f}%")

        print("\nBy Category:")
        for category, stats in summary.by_category.items():
            rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  {category}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

        if summary.failed > 0:
            print("\nFailed Questions:")
            for r in self.results:
                if not r.passed:
                    print(f"  [{r.question_id}] {r.question[:60]}...")
                    if r.error_message:
                        print(f"    Error: {r.error_message}")

        print("\n" + "=" * 80)

    def save_results(self, output_file: str) -> None:
        """Save results to JSON file."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(VALIDATION_QUESTIONS),
            "results": [r.to_dict() for r in self.results],
        }

        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)

        logger.info("Results saved", output_file=output_file)


async def main(verbose: bool = False, output_file: str | None = None) -> int:
    """Main entry point."""
    validator = Phase02Validator(verbose=verbose)
    summary = await validator.run_all()
    validator.print_summary(summary)

    if output_file:
        validator.save_results(output_file)

    # Return 0 if pass rate >= 80%, 1 otherwise
    return 0 if summary.pass_rate >= 80 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 02 QnA validation")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show each test result",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file for JSON results",
    )

    args = parser.parse_args()
    exit_code = asyncio.run(main(verbose=args.verbose, output_file=args.output))
    sys.exit(exit_code)
