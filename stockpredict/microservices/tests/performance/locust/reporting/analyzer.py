"""
Load test result analyzer.

Parses Locust CSV output and provides analysis utilities.
"""

import csv
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class EndpointStats:
    """Statistics for a single endpoint."""
    name: str
    method: str
    request_count: int
    failure_count: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    p90_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_sec: float

    @property
    def success_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return ((self.request_count - self.failure_count) / self.request_count) * 100

    @property
    def failure_rate(self) -> float:
        return 100 - self.success_rate

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "method": self.method,
            "request_count": self.request_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 2),
            "avg_response_time_ms": round(self.avg_response_time, 2),
            "min_response_time_ms": round(self.min_response_time, 2),
            "max_response_time_ms": round(self.max_response_time, 2),
            "p95_response_time_ms": round(self.p95_response_time, 2),
            "p99_response_time_ms": round(self.p99_response_time, 2),
            "requests_per_sec": round(self.requests_per_sec, 2),
        }


@dataclass
class LoadTestResults:
    """Complete load test results."""
    timestamp: datetime
    duration_seconds: float
    total_users: int
    endpoints: List[EndpointStats] = field(default_factory=list)
    failures: List[Dict] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)

    @property
    def total_requests(self) -> int:
        return sum(e.request_count for e in self.endpoints)

    @property
    def total_failures(self) -> int:
        return sum(e.failure_count for e in self.endpoints)

    @property
    def overall_success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return ((self.total_requests - self.total_failures) / self.total_requests) * 100

    @property
    def avg_response_time(self) -> float:
        if not self.endpoints:
            return 0.0
        total = sum(e.avg_response_time * e.request_count for e in self.endpoints)
        return total / self.total_requests if self.total_requests > 0 else 0.0

    @property
    def requests_per_second(self) -> float:
        if self.duration_seconds == 0:
            return 0.0
        return self.total_requests / self.duration_seconds

    def get_slowest_endpoints(self, n: int = 5) -> List[EndpointStats]:
        return sorted(self.endpoints, key=lambda x: x.p95_response_time, reverse=True)[:n]

    def get_failing_endpoints(self) -> List[EndpointStats]:
        return [e for e in self.endpoints if e.failure_count > 0]

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "total_users": self.total_users,
            "summary": {
                "total_requests": self.total_requests,
                "total_failures": self.total_failures,
                "success_rate": round(self.overall_success_rate, 2),
                "avg_response_time_ms": round(self.avg_response_time, 2),
                "requests_per_second": round(self.requests_per_second, 2),
            },
            "endpoints": [e.to_dict() for e in self.endpoints],
            "failures": self.failures,
        }


class LoadTestAnalyzer:
    """Analyzer for Locust load test results."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)

    def parse_results(self, prefix: str) -> LoadTestResults:
        """Parse Locust CSV results."""
        stats_file = self.results_dir / f"{prefix}_stats.csv"
        failures_file = self.results_dir / f"{prefix}_failures.csv"
        history_file = self.results_dir / f"{prefix}_stats_history.csv"

        endpoints = self._parse_stats(stats_file)
        failures = self._parse_failures(failures_file) if failures_file.exists() else []
        history = self._parse_history(history_file) if history_file.exists() else []

        # Extract metadata
        timestamp = datetime.now()
        duration = self._calculate_duration(history)
        total_users = self._get_max_users(history)

        return LoadTestResults(
            timestamp=timestamp,
            duration_seconds=duration,
            total_users=total_users,
            endpoints=endpoints,
            failures=failures,
            history=history,
        )

    def _parse_stats(self, filepath: Path) -> List[EndpointStats]:
        """Parse stats CSV file."""
        endpoints = []

        if not filepath.exists():
            return endpoints

        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Name') == 'Aggregated':
                    continue  # Skip aggregated row

                try:
                    endpoint = EndpointStats(
                        name=row.get('Name', ''),
                        method=row.get('Type', 'GET'),
                        request_count=int(row.get('Request Count', 0)),
                        failure_count=int(row.get('Failure Count', 0)),
                        avg_response_time=float(row.get('Average Response Time', 0)),
                        min_response_time=float(row.get('Min Response Time', 0)),
                        max_response_time=float(row.get('Max Response Time', 0)),
                        median_response_time=float(row.get('Median Response Time', 0)),
                        p90_response_time=float(row.get('90%', 0)),
                        p95_response_time=float(row.get('95%', 0)),
                        p99_response_time=float(row.get('99%', 0)),
                        requests_per_sec=float(row.get('Requests/s', 0)),
                    )
                    endpoints.append(endpoint)
                except (ValueError, KeyError):
                    continue

        return endpoints

    def _parse_failures(self, filepath: Path) -> List[Dict]:
        """Parse failures CSV file."""
        failures = []

        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                failures.append({
                    "method": row.get('Method', ''),
                    "name": row.get('Name', ''),
                    "error": row.get('Error', ''),
                    "count": int(row.get('Occurrences', 0)),
                })

        return failures

    def _parse_history(self, filepath: Path) -> List[Dict]:
        """Parse history CSV file."""
        history = []

        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                history.append({
                    "timestamp": row.get('Timestamp', ''),
                    "user_count": int(row.get('User Count', 0)),
                    "requests_per_sec": float(row.get('Requests/s', 0)),
                    "failures_per_sec": float(row.get('Failures/s', 0)),
                })

        return history

    def _calculate_duration(self, history: List[Dict]) -> float:
        """Calculate test duration from history."""
        if len(history) < 2:
            return 0.0

        # Assuming 1-second intervals
        return float(len(history))

    def _get_max_users(self, history: List[Dict]) -> int:
        """Get maximum user count from history."""
        if not history:
            return 0
        return max(h.get('user_count', 0) for h in history)

    def validate_thresholds(
        self,
        results: LoadTestResults,
        thresholds: Dict[str, Dict]
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Validate results against thresholds.

        Args:
            results: Load test results
            thresholds: Dict of endpoint -> threshold dict
                       e.g., {"health": {"p95": 100, "success_rate": 99.9}}

        Returns:
            Dict of endpoint -> (passed, message)
        """
        validations = {}

        for endpoint in results.endpoints:
            endpoint_key = endpoint.name.replace('/', '_').strip('_')
            threshold = thresholds.get(endpoint_key, {})

            if not threshold:
                continue

            passed = True
            messages = []

            if 'p95' in threshold and endpoint.p95_response_time > threshold['p95']:
                passed = False
                messages.append(
                    f"P95 {endpoint.p95_response_time:.0f}ms > {threshold['p95']}ms"
                )

            if 'p99' in threshold and endpoint.p99_response_time > threshold['p99']:
                passed = False
                messages.append(
                    f"P99 {endpoint.p99_response_time:.0f}ms > {threshold['p99']}ms"
                )

            if 'success_rate' in threshold and endpoint.success_rate < threshold['success_rate']:
                passed = False
                messages.append(
                    f"Success rate {endpoint.success_rate:.1f}% < {threshold['success_rate']}%"
                )

            if 'avg' in threshold and endpoint.avg_response_time > threshold['avg']:
                passed = False
                messages.append(
                    f"Avg {endpoint.avg_response_time:.0f}ms > {threshold['avg']}ms"
                )

            validations[endpoint.name] = (
                passed,
                "; ".join(messages) if messages else "All thresholds met"
            )

        return validations

    def find_performance_issues(self, results: LoadTestResults) -> List[Dict]:
        """Identify potential performance issues."""
        issues = []

        for endpoint in results.endpoints:
            # High failure rate
            if endpoint.failure_rate > 1:
                issues.append({
                    "severity": "high" if endpoint.failure_rate > 5 else "medium",
                    "type": "high_failure_rate",
                    "endpoint": endpoint.name,
                    "message": f"Failure rate: {endpoint.failure_rate:.1f}%",
                })

            # Slow P99
            if endpoint.p99_response_time > 5000:
                issues.append({
                    "severity": "high",
                    "type": "slow_p99",
                    "endpoint": endpoint.name,
                    "message": f"P99 response time: {endpoint.p99_response_time:.0f}ms",
                })
            elif endpoint.p99_response_time > 2000:
                issues.append({
                    "severity": "medium",
                    "type": "slow_p99",
                    "endpoint": endpoint.name,
                    "message": f"P99 response time: {endpoint.p99_response_time:.0f}ms",
                })

            # High variance
            if endpoint.max_response_time > endpoint.avg_response_time * 10:
                issues.append({
                    "severity": "medium",
                    "type": "high_variance",
                    "endpoint": endpoint.name,
                    "message": f"Max ({endpoint.max_response_time:.0f}ms) is 10x+ avg ({endpoint.avg_response_time:.0f}ms)",
                })

        return sorted(issues, key=lambda x: 0 if x['severity'] == 'high' else 1)

    def export_json(self, results: LoadTestResults, filepath: str):
        """Export results to JSON."""
        with open(filepath, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)

    def export_markdown(self, results: LoadTestResults, filepath: str):
        """Export results to Markdown."""
        lines = [
            "# Load Test Results",
            "",
            f"**Date:** {results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {results.duration_seconds:.0f} seconds",
            f"**Peak Users:** {results.total_users}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Requests | {results.total_requests:,} |",
            f"| Total Failures | {results.total_failures:,} |",
            f"| Success Rate | {results.overall_success_rate:.2f}% |",
            f"| Avg Response Time | {results.avg_response_time:.2f} ms |",
            f"| Requests/sec | {results.requests_per_second:.2f} |",
            "",
            "## Endpoint Performance",
            "",
            "| Endpoint | Requests | Failures | Avg (ms) | P95 (ms) | P99 (ms) |",
            "|----------|----------|----------|----------|----------|----------|",
        ]

        for ep in results.endpoints:
            lines.append(
                f"| {ep.name} | {ep.request_count:,} | {ep.failure_count:,} | "
                f"{ep.avg_response_time:.0f} | {ep.p95_response_time:.0f} | "
                f"{ep.p99_response_time:.0f} |"
            )

        if results.failures:
            lines.extend([
                "",
                "## Failures",
                "",
                "| Method | Endpoint | Error | Count |",
                "|--------|----------|-------|-------|",
            ])
            for failure in results.failures:
                lines.append(
                    f"| {failure['method']} | {failure['name']} | "
                    f"{failure['error'][:50]}... | {failure['count']} |"
                )

        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
