"""
Load test result comparator.

Compares results across different test runs to identify performance trends.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .analyzer import LoadTestAnalyzer, LoadTestResults


@dataclass
class ComparisonResult:
    """Result of comparing two test runs."""
    endpoint: str
    baseline_avg: float
    current_avg: float
    change_percent: float
    baseline_p95: float
    current_p95: float
    p95_change_percent: float
    status: str  # improved, degraded, stable

    def to_dict(self) -> Dict:
        return {
            "endpoint": self.endpoint,
            "baseline_avg_ms": round(self.baseline_avg, 2),
            "current_avg_ms": round(self.current_avg, 2),
            "avg_change_percent": round(self.change_percent, 2),
            "baseline_p95_ms": round(self.baseline_p95, 2),
            "current_p95_ms": round(self.current_p95, 2),
            "p95_change_percent": round(self.p95_change_percent, 2),
            "status": self.status,
        }


class ResultComparator:
    """Compare load test results across runs."""

    def __init__(
        self,
        degradation_threshold: float = 10.0,
        improvement_threshold: float = -10.0
    ):
        """
        Initialize comparator.

        Args:
            degradation_threshold: % increase to flag as degradation (default 10%)
            improvement_threshold: % decrease to flag as improvement (default -10%)
        """
        self.degradation_threshold = degradation_threshold
        self.improvement_threshold = improvement_threshold

    def compare(
        self,
        baseline: LoadTestResults,
        current: LoadTestResults
    ) -> List[ComparisonResult]:
        """
        Compare two test runs.

        Args:
            baseline: Baseline/reference test results
            current: Current test results to compare

        Returns:
            List of comparison results per endpoint
        """
        results = []

        # Build lookup for baseline endpoints
        baseline_map = {ep.name: ep for ep in baseline.endpoints}

        for current_ep in current.endpoints:
            baseline_ep = baseline_map.get(current_ep.name)

            if not baseline_ep:
                continue  # New endpoint, skip

            # Calculate changes
            avg_change = self._calculate_change(
                baseline_ep.avg_response_time,
                current_ep.avg_response_time
            )
            p95_change = self._calculate_change(
                baseline_ep.p95_response_time,
                current_ep.p95_response_time
            )

            # Determine status
            status = self._determine_status(avg_change, p95_change)

            results.append(ComparisonResult(
                endpoint=current_ep.name,
                baseline_avg=baseline_ep.avg_response_time,
                current_avg=current_ep.avg_response_time,
                change_percent=avg_change,
                baseline_p95=baseline_ep.p95_response_time,
                current_p95=current_ep.p95_response_time,
                p95_change_percent=p95_change,
                status=status,
            ))

        return sorted(results, key=lambda x: x.change_percent, reverse=True)

    def _calculate_change(self, baseline: float, current: float) -> float:
        """Calculate percentage change."""
        if baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100

    def _determine_status(self, avg_change: float, p95_change: float) -> str:
        """Determine status based on changes."""
        # Use the worse of avg and p95 changes
        max_change = max(avg_change, p95_change)

        if max_change >= self.degradation_threshold:
            return "degraded"
        elif max_change <= self.improvement_threshold:
            return "improved"
        else:
            return "stable"

    def generate_summary(self, comparisons: List[ComparisonResult]) -> Dict:
        """Generate comparison summary."""
        total = len(comparisons)
        improved = sum(1 for c in comparisons if c.status == "improved")
        degraded = sum(1 for c in comparisons if c.status == "degraded")
        stable = sum(1 for c in comparisons if c.status == "stable")

        avg_changes = [c.change_percent for c in comparisons]
        overall_change = sum(avg_changes) / len(avg_changes) if avg_changes else 0

        return {
            "total_endpoints": total,
            "improved": improved,
            "degraded": degraded,
            "stable": stable,
            "overall_change_percent": round(overall_change, 2),
            "status": "degraded" if degraded > 0 else ("improved" if improved > 0 else "stable"),
        }

    def generate_report(
        self,
        baseline: LoadTestResults,
        current: LoadTestResults,
        output_path: str
    ):
        """Generate comparison report."""
        comparisons = self.compare(baseline, current)
        summary = self.generate_summary(comparisons)

        lines = [
            "# Load Test Comparison Report",
            "",
            f"**Baseline:** {baseline.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"**Current:** {current.timestamp.strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            f"| Status | Count |",
            f"|--------|-------|",
            f"| ✅ Improved | {summary['improved']} |",
            f"| ⚠️ Degraded | {summary['degraded']} |",
            f"| ➖ Stable | {summary['stable']} |",
            f"| **Total** | {summary['total_endpoints']} |",
            "",
            f"**Overall Change:** {summary['overall_change_percent']:+.1f}%",
            "",
            "## Endpoint Details",
            "",
            "| Endpoint | Baseline Avg | Current Avg | Change | Status |",
            "|----------|-------------|-------------|--------|--------|",
        ]

        status_emoji = {"improved": "✅", "degraded": "⚠️", "stable": "➖"}

        for comp in comparisons:
            emoji = status_emoji.get(comp.status, "")
            lines.append(
                f"| {comp.endpoint} | {comp.baseline_avg:.0f}ms | "
                f"{comp.current_avg:.0f}ms | {comp.change_percent:+.1f}% | {emoji} {comp.status} |"
            )

        if summary['degraded'] > 0:
            lines.extend([
                "",
                "## ⚠️ Degraded Endpoints",
                "",
                "The following endpoints showed performance degradation:",
                "",
            ])
            for comp in comparisons:
                if comp.status == "degraded":
                    lines.append(
                        f"- **{comp.endpoint}**: Avg increased {comp.change_percent:.1f}% "
                        f"({comp.baseline_avg:.0f}ms → {comp.current_avg:.0f}ms)"
                    )

        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

    def generate_json_report(
        self,
        baseline: LoadTestResults,
        current: LoadTestResults,
        output_path: str
    ):
        """Generate JSON comparison report."""
        comparisons = self.compare(baseline, current)
        summary = self.generate_summary(comparisons)

        report = {
            "generated_at": datetime.now().isoformat(),
            "baseline": {
                "timestamp": baseline.timestamp.isoformat(),
                "total_requests": baseline.total_requests,
                "success_rate": baseline.overall_success_rate,
            },
            "current": {
                "timestamp": current.timestamp.isoformat(),
                "total_requests": current.total_requests,
                "success_rate": current.overall_success_rate,
            },
            "summary": summary,
            "comparisons": [c.to_dict() for c in comparisons],
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)


def compare_runs(
    results_dir: str,
    baseline_prefix: str,
    current_prefix: str,
    output_format: str = "markdown"
) -> str:
    """
    Convenience function to compare two test runs.

    Args:
        results_dir: Directory containing CSV results
        baseline_prefix: Prefix for baseline CSV files
        current_prefix: Prefix for current CSV files
        output_format: "markdown" or "json"

    Returns:
        Path to generated report
    """
    analyzer = LoadTestAnalyzer(results_dir)
    comparator = ResultComparator()

    baseline = analyzer.parse_results(baseline_prefix)
    current = analyzer.parse_results(current_prefix)

    output_path = Path(results_dir) / f"comparison_{current_prefix}.{'md' if output_format == 'markdown' else 'json'}"

    if output_format == "markdown":
        comparator.generate_report(baseline, current, str(output_path))
    else:
        comparator.generate_json_report(baseline, current, str(output_path))

    return str(output_path)
