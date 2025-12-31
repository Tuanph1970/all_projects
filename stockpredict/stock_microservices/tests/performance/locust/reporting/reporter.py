"""
Load test HTML report generator.

Creates detailed HTML reports from load test results.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from .analyzer import LoadTestResults, EndpointStats


class LoadTestReporter:
    """Generate HTML reports for load test results."""

    def __init__(self, results: LoadTestResults, thresholds: Optional[Dict] = None):
        self.results = results
        self.thresholds = thresholds or {}

    def generate_html(self, output_path: str):
        """Generate comprehensive HTML report."""
        html = self._build_html()
        with open(output_path, 'w') as f:
            f.write(html)

    def _build_html(self) -> str:
        """Build HTML report content."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Load Test Report - Stock Helper</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        {self._get_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 Load Test Report</h1>
            <p class="subtitle">Stock Helper Microservices</p>
            <p class="timestamp">{self.results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        {self._build_summary_section()}
        {self._build_charts_section()}
        {self._build_endpoints_section()}
        {self._build_failures_section()}
        {self._build_recommendations_section()}
    </div>

    <script>
        {self._get_chart_scripts()}
    </script>
</body>
</html>"""

    def _get_styles(self) -> str:
        """CSS styles for the report."""
        return """
        :root {
            --primary: #2563eb;
            --success: #16a34a;
            --warning: #d97706;
            --danger: #dc2626;
            --bg-light: #f8fafc;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-light);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            text-align: center;
            margin-bottom: 2rem;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 1.2rem;
        }

        .timestamp {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }

        .card {
            background: var(--bg-card);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }

        .card h2 {
            font-size: 1.3rem;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .metric {
            background: var(--bg-light);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }

        .metric-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }

        .metric.success .metric-value { color: var(--success); }
        .metric.warning .metric-value { color: var(--warning); }
        .metric.danger .metric-value { color: var(--danger); }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        th {
            background: var(--bg-light);
            font-weight: 600;
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
        }

        tr:hover {
            background: var(--bg-light);
        }

        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .status-pass { background: #dcfce7; color: var(--success); }
        .status-fail { background: #fee2e2; color: var(--danger); }
        .status-warn { background: #fef3c7; color: var(--warning); }

        .chart-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1rem;
        }

        .chart-box {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 1rem;
        }

        .recommendations {
            list-style: none;
        }

        .recommendations li {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 8px;
            border-left: 4px solid;
        }

        .recommendations li.high {
            background: #fee2e2;
            border-color: var(--danger);
        }

        .recommendations li.medium {
            background: #fef3c7;
            border-color: var(--warning);
        }

        .recommendations li.low {
            background: #dcfce7;
            border-color: var(--success);
        }
        """

    def _build_summary_section(self) -> str:
        """Build summary metrics section."""
        success_class = "success" if self.results.overall_success_rate >= 99 else (
            "warning" if self.results.overall_success_rate >= 95 else "danger"
        )

        return f"""
        <section class="card">
            <h2>📊 Test Summary</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-value">{self.results.duration_seconds:.0f}s</div>
                    <div class="metric-label">Duration</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{self.results.total_users}</div>
                    <div class="metric-label">Peak Users</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{self.results.total_requests:,}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric {success_class}">
                    <div class="metric-value">{self.results.overall_success_rate:.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{self.results.avg_response_time:.0f}ms</div>
                    <div class="metric-label">Avg Response Time</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{self.results.requests_per_second:.1f}</div>
                    <div class="metric-label">Requests/sec</div>
                </div>
            </div>
        </section>
        """

    def _build_charts_section(self) -> str:
        """Build charts section."""
        return """
        <section class="card">
            <h2>📈 Performance Charts</h2>
            <div class="chart-container">
                <div class="chart-box">
                    <canvas id="responseTimeChart"></canvas>
                </div>
                <div class="chart-box">
                    <canvas id="requestDistChart"></canvas>
                </div>
            </div>
        </section>
        """

    def _build_endpoints_section(self) -> str:
        """Build endpoints performance table."""
        rows = []
        for ep in sorted(self.results.endpoints, key=lambda x: x.request_count, reverse=True):
            status = "pass" if ep.success_rate >= 99 else ("warn" if ep.success_rate >= 95 else "fail")
            rows.append(f"""
                <tr>
                    <td>{ep.method}</td>
                    <td>{ep.name}</td>
                    <td>{ep.request_count:,}</td>
                    <td><span class="status-badge status-{status}">{ep.success_rate:.1f}%</span></td>
                    <td>{ep.avg_response_time:.0f}</td>
                    <td>{ep.p95_response_time:.0f}</td>
                    <td>{ep.p99_response_time:.0f}</td>
                    <td>{ep.requests_per_sec:.1f}</td>
                </tr>
            """)

        return f"""
        <section class="card">
            <h2>🎯 Endpoint Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Endpoint</th>
                        <th>Requests</th>
                        <th>Success</th>
                        <th>Avg (ms)</th>
                        <th>P95 (ms)</th>
                        <th>P99 (ms)</th>
                        <th>Req/s</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </section>
        """

    def _build_failures_section(self) -> str:
        """Build failures section."""
        if not self.results.failures:
            return """
            <section class="card">
                <h2>❌ Failures</h2>
                <p style="color: var(--success);">No failures recorded! 🎉</p>
            </section>
            """

        rows = []
        for failure in self.results.failures:
            rows.append(f"""
                <tr>
                    <td>{failure['method']}</td>
                    <td>{failure['name']}</td>
                    <td>{failure['error'][:100]}...</td>
                    <td>{failure['count']}</td>
                </tr>
            """)

        return f"""
        <section class="card">
            <h2>❌ Failures</h2>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Endpoint</th>
                        <th>Error</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </section>
        """

    def _build_recommendations_section(self) -> str:
        """Build recommendations section."""
        recommendations = self._generate_recommendations()

        if not recommendations:
            return """
            <section class="card">
                <h2>💡 Recommendations</h2>
                <p style="color: var(--success);">All performance metrics look good! No recommendations at this time.</p>
            </section>
            """

        items = []
        for rec in recommendations:
            items.append(f'<li class="{rec["severity"]}">{rec["message"]}</li>')

        return f"""
        <section class="card">
            <h2>💡 Recommendations</h2>
            <ul class="recommendations">
                {"".join(items)}
            </ul>
        </section>
        """

    def _generate_recommendations(self) -> List[Dict]:
        """Generate performance recommendations."""
        recommendations = []

        # Check overall success rate
        if self.results.overall_success_rate < 99:
            recommendations.append({
                "severity": "high" if self.results.overall_success_rate < 95 else "medium",
                "message": f"Success rate ({self.results.overall_success_rate:.1f}%) is below 99%. Investigate failing endpoints."
            })

        # Check for slow endpoints
        for ep in self.results.endpoints:
            if ep.p99_response_time > 5000:
                recommendations.append({
                    "severity": "high",
                    "message": f"Endpoint {ep.name} has P99 > 5s ({ep.p99_response_time:.0f}ms). Consider caching or optimization."
                })
            elif ep.p99_response_time > 2000:
                recommendations.append({
                    "severity": "medium",
                    "message": f"Endpoint {ep.name} has P99 > 2s ({ep.p99_response_time:.0f}ms). Monitor for degradation."
                })

        # Check throughput
        if self.results.requests_per_second < 10:
            recommendations.append({
                "severity": "medium",
                "message": f"Low throughput ({self.results.requests_per_second:.1f} req/s). Consider horizontal scaling."
            })

        return recommendations

    def _get_chart_scripts(self) -> str:
        """JavaScript for charts."""
        # Prepare data for charts
        endpoints = sorted(self.results.endpoints, key=lambda x: x.request_count, reverse=True)[:10]
        labels = [ep.name[:30] for ep in endpoints]
        avg_times = [ep.avg_response_time for ep in endpoints]
        p95_times = [ep.p95_response_time for ep in endpoints]
        request_counts = [ep.request_count for ep in endpoints]

        return f"""
        // Response Time Chart
        new Chart(document.getElementById('responseTimeChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{
                        label: 'Avg Response Time (ms)',
                        data: {json.dumps(avg_times)},
                        backgroundColor: 'rgba(37, 99, 235, 0.6)',
                        borderColor: 'rgba(37, 99, 235, 1)',
                        borderWidth: 1
                    }},
                    {{
                        label: 'P95 Response Time (ms)',
                        data: {json.dumps(p95_times)},
                        backgroundColor: 'rgba(220, 38, 38, 0.6)',
                        borderColor: 'rgba(220, 38, 38, 1)',
                        borderWidth: 1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Response Times by Endpoint'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Response Time (ms)'
                        }}
                    }}
                }}
            }}
        }});

        // Request Distribution Chart
        new Chart(document.getElementById('requestDistChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    data: {json.dumps(request_counts)},
                    backgroundColor: [
                        '#2563eb', '#16a34a', '#d97706', '#dc2626', '#8b5cf6',
                        '#06b6d4', '#ec4899', '#f59e0b', '#10b981', '#6366f1'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Request Distribution'
                    }},
                    legend: {{
                        position: 'right'
                    }}
                }}
            }}
        }});
        """
