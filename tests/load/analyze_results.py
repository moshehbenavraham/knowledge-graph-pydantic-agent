"""
Performance metrics collection and analysis for load test results.

Analyzes Locust test results and generates performance reports.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def analyze_performance_results(stats_file: str) -> dict[str, Any]:
    """
    Analyze Locust statistics and generate performance report.

    Args:
        stats_file: Path to Locust stats JSON file

    Returns:
        Performance report dictionary
    """
    with open(stats_file) as f:
        stats = json.load(f)

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "summary": {
            "total_requests": stats.get("total_requests", 0),
            "failed_requests": stats.get("failed_requests", 0),
            "failure_rate": stats.get("failure_rate", 0.0),
            "avg_response_time": stats.get("avg_response_time", 0.0),
            "p50_response_time": stats.get("p50", 0.0),
            "p95_response_time": stats.get("p95", 0.0),
            "p99_response_time": stats.get("p99", 0.0),
            "requests_per_second": stats.get("rps", 0.0),
            "total_duration_seconds": stats.get("duration", 0.0),
        },
        "by_endpoint": {},
        "slo_compliance": {},
        "recommendations": [],
    }

    # Analyze by endpoint
    endpoints = stats.get("endpoints", [])
    for endpoint in endpoints:
        endpoint_name = endpoint.get("name", "unknown")
        report["by_endpoint"][endpoint_name] = {
            "total_requests": endpoint.get("total", 0),
            "failures": endpoint.get("failures", 0),
            "failure_rate": endpoint.get("failure_rate", 0.0),
            "avg_response_time": endpoint.get("avg", 0.0),
            "p50": endpoint.get("p50", 0.0),
            "p95": endpoint.get("p95", 0.0),
            "p99": endpoint.get("p99", 0.0),
            "min": endpoint.get("min", 0.0),
            "max": endpoint.get("max", 0.0),
            "requests_per_second": endpoint.get("rps", 0.0),
        }

    # Check SLO compliance
    chat_endpoint = report["by_endpoint"].get("/api/v1/chat [POST]", {})
    search_endpoint = report["by_endpoint"].get("/api/v1/search [vector]", {})

    slo_checks = {
        "chat_p50_met": chat_endpoint.get("p50", float("inf")) < 500,
        "chat_p95_met": chat_endpoint.get("p95", float("inf")) < 1500,
        "search_p50_met": search_endpoint.get("p50", float("inf")) < 200,
        "search_p95_met": search_endpoint.get("p95", float("inf")) < 500,
        "overall_failure_rate_met": report["summary"]["failure_rate"] < 0.05,
    }

    report["slo_compliance"] = {
        "all_met": all(slo_checks.values()),
        "checks": slo_checks,
        "details": {
            "chat_p50": {
                "target_ms": 500,
                "actual_ms": chat_endpoint.get("p50", 0),
                "met": slo_checks["chat_p50_met"],
            },
            "chat_p95": {
                "target_ms": 1500,
                "actual_ms": chat_endpoint.get("p95", 0),
                "met": slo_checks["chat_p95_met"],
            },
            "search_p50": {
                "target_ms": 200,
                "actual_ms": search_endpoint.get("p50", 0),
                "met": slo_checks["search_p50_met"],
            },
            "search_p95": {
                "target_ms": 500,
                "actual_ms": search_endpoint.get("p95", 0),
                "met": slo_checks["search_p95_met"],
            },
            "failure_rate": {
                "target": 0.05,
                "actual": report["summary"]["failure_rate"],
                "met": slo_checks["overall_failure_rate_met"],
            },
        },
    }

    # Generate recommendations
    recommendations = []

    # Check failure rate
    if report["summary"]["failure_rate"] > 0.05:
        recommendations.append(
            {
                "severity": "high",
                "category": "reliability",
                "message": (
                    f"High failure rate: {report['summary']['failure_rate']:.2%}. "
                    f"Target is <5%. Investigate error logs and add error handling."
                ),
            }
        )

    # Check response times
    if not slo_checks["chat_p95_met"]:
        recommendations.append(
            {
                "severity": "medium",
                "category": "performance",
                "message": (
                    f"Chat P95 ({chat_endpoint.get('p95', 0):.0f}ms) exceeds target "
                    f"(1500ms). Consider caching, query optimization, or scaling."
                ),
            }
        )

    if not slo_checks["search_p50_met"]:
        recommendations.append(
            {
                "severity": "high",
                "category": "performance",
                "message": (
                    f"Search P50 ({search_endpoint.get('p50', 0):.0f}ms) exceeds target "
                    f"(200ms). Optimize vector search or add caching."
                ),
            }
        )

    # Check for slow endpoints
    for endpoint_name, metrics in report["by_endpoint"].items():
        if metrics["p95"] > 2000:
            recommendations.append(
                {
                    "severity": "medium",
                    "category": "performance",
                    "message": (
                        f"Endpoint '{endpoint_name}' has high P95 latency "
                        f"({metrics['p95']:.0f}ms). Profile and optimize."
                    ),
                }
            )

    # Check throughput
    if report["summary"]["requests_per_second"] < 10:
        recommendations.append(
            {
                "severity": "low",
                "category": "capacity",
                "message": (
                    f"Low throughput: {report['summary']['requests_per_second']:.1f} RPS. "
                    f"Consider horizontal scaling or connection pool tuning."
                ),
            }
        )

    report["recommendations"] = recommendations

    return report


def generate_markdown_report(report: dict[str, Any]) -> str:
    """
    Generate markdown-formatted performance report.

    Args:
        report: Performance report dictionary

    Returns:
        Markdown-formatted report
    """
    md = [
        "# Load Test Performance Report",
        "",
        f"**Generated**: {report['timestamp']}",
        "",
        "## Executive Summary",
        "",
        f"- **Total Requests**: {report['summary']['total_requests']:,}",
        f"- **Failed Requests**: {report['summary']['failed_requests']:,}",
        f"- **Failure Rate**: {report['summary']['failure_rate']:.2%}",
        f"- **Avg Response Time**: {report['summary']['avg_response_time']:.0f}ms",
        f"- **P50 Response Time**: {report['summary']['p50_response_time']:.0f}ms",
        f"- **P95 Response Time**: {report['summary']['p95_response_time']:.0f}ms",
        f"- **P99 Response Time**: {report['summary']['p99_response_time']:.0f}ms",
        f"- **Throughput**: {report['summary']['requests_per_second']:.1f} RPS",
        "",
        "## SLO Compliance",
        "",
    ]

    if report["slo_compliance"]["all_met"]:
        md.append("✅ **All SLO targets met**")
    else:
        md.append("❌ **Some SLO targets not met**")

    md.extend(["", "### Detailed Compliance", ""])

    for check_name, details in report["slo_compliance"]["details"].items():
        status = "✅" if details["met"] else "❌"
        if "target_ms" in details:
            md.append(
                f"- {status} **{check_name}**: {details['actual_ms']:.0f}ms "
                f"(target: {details['target_ms']}ms)"
            )
        else:
            md.append(
                f"- {status} **{check_name}**: {details['actual']:.2%} "
                f"(target: {details['target']:.2%})"
            )

    md.extend(["", "## Performance by Endpoint", ""])

    # Sort endpoints by total requests
    sorted_endpoints = sorted(
        report["by_endpoint"].items(),
        key=lambda x: x[1]["total_requests"],
        reverse=True,
    )

    md.append("| Endpoint | Requests | Failures | P50 | P95 | P99 | RPS |")
    md.append("|----------|----------|----------|-----|-----|-----|-----|")

    for endpoint_name, metrics in sorted_endpoints:
        md.append(
            f"| {endpoint_name} | {metrics['total_requests']:,} | "
            f"{metrics['failures']} | {metrics['p50']:.0f}ms | "
            f"{metrics['p95']:.0f}ms | {metrics['p99']:.0f}ms | "
            f"{metrics['requests_per_second']:.1f} |"
        )

    md.extend(["", "## Recommendations", ""])

    if not report["recommendations"]:
        md.append("✅ No issues detected. System performing within targets.")
    else:
        for rec in report["recommendations"]:
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec["severity"], "⚪")
            md.append(f"{severity_emoji} **{rec['category'].title()}** - {rec['message']}")

    return "\n".join(md)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Locust load test results and generate reports"
    )
    parser.add_argument(
        "stats_file",
        help="Path to Locust statistics JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for report (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    args = parser.parse_args()

    # Check if stats file exists
    if not Path(args.stats_file).exists():
        print(f"Error: Stats file '{args.stats_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Analyze results
    try:
        report = analyze_performance_results(args.stats_file)
    except Exception as e:
        print(f"Error analyzing results: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate output
    if args.format == "json":
        output = json.dumps(report, indent=2)
    else:
        output = generate_markdown_report(report)

    # Write output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Report written to {args.output}")
    else:
        print(output)

    # Exit with error code if SLOs not met
    if not report["slo_compliance"]["all_met"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
