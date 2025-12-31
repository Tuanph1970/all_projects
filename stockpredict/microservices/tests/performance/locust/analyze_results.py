#!/usr/bin/env python3
"""
CLI tool for analyzing load test results.

Usage:
    python analyze_results.py analyze <prefix> [--output json|markdown|html]
    python analyze_results.py compare <baseline> <current>
    python analyze_results.py validate <prefix> --thresholds <file>
"""

import argparse
import json
import sys
from pathlib import Path

from reporting.analyzer import LoadTestAnalyzer
from reporting.reporter import LoadTestReporter
from reporting.comparator import ResultComparator


def cmd_analyze(args):
    """Analyze load test results."""
    analyzer = LoadTestAnalyzer(args.results_dir)

    try:
        results = analyzer.parse_results(args.prefix)
    except Exception as e:
        print(f"Error parsing results: {e}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("LOAD TEST ANALYSIS")
    print(f"{'='*60}\n")

    print(f"Duration: {results.duration_seconds:.0f} seconds")
    print(f"Peak Users: {results.total_users}")
    print(f"Total Requests: {results.total_requests:,}")
    print(f"Total Failures: {results.total_failures:,}")
    print(f"Success Rate: {results.overall_success_rate:.2f}%")
    print(f"Avg Response Time: {results.avg_response_time:.2f}ms")
    print(f"Requests/sec: {results.requests_per_second:.2f}")

    print(f"\n{'='*60}")
    print("SLOWEST ENDPOINTS (P95)")
    print(f"{'='*60}\n")

    for ep in results.get_slowest_endpoints(5):
        print(f"  {ep.name}")
        print(f"    Avg: {ep.avg_response_time:.0f}ms | P95: {ep.p95_response_time:.0f}ms | P99: {ep.p99_response_time:.0f}ms")

    # Check for issues
    issues = analyzer.find_performance_issues(results)
    if issues:
        print(f"\n{'='*60}")
        print("PERFORMANCE ISSUES DETECTED")
        print(f"{'='*60}\n")

        for issue in issues:
            severity_icon = "🔴" if issue['severity'] == 'high' else "🟡"
            print(f"  {severity_icon} [{issue['type']}] {issue['endpoint']}")
            print(f"     {issue['message']}")

    # Export based on format
    output_base = Path(args.results_dir) / f"{args.prefix}_analysis"

    if args.output in ['json', 'all']:
        json_path = f"{output_base}.json"
        analyzer.export_json(results, json_path)
        print(f"\nJSON report: {json_path}")

    if args.output in ['markdown', 'all']:
        md_path = f"{output_base}.md"
        analyzer.export_markdown(results, md_path)
        print(f"Markdown report: {md_path}")

    if args.output in ['html', 'all']:
        html_path = f"{output_base}.html"
        reporter = LoadTestReporter(results)
        reporter.generate_html(html_path)
        print(f"HTML report: {html_path}")

    print()


def cmd_compare(args):
    """Compare two test runs."""
    analyzer = LoadTestAnalyzer(args.results_dir)
    comparator = ResultComparator()

    try:
        baseline = analyzer.parse_results(args.baseline)
        current = analyzer.parse_results(args.current)
    except Exception as e:
        print(f"Error parsing results: {e}")
        sys.exit(1)

    comparisons = comparator.compare(baseline, current)
    summary = comparator.generate_summary(comparisons)

    print(f"\n{'='*60}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*60}\n")

    print(f"Baseline: {baseline.timestamp.strftime('%Y-%m-%d %H:%M')}")
    print(f"Current:  {current.timestamp.strftime('%Y-%m-%d %H:%M')}")
    print()

    print(f"Overall Status: {summary['status'].upper()}")
    print(f"  ✅ Improved: {summary['improved']}")
    print(f"  ⚠️  Degraded: {summary['degraded']}")
    print(f"  ➖ Stable: {summary['stable']}")
    print(f"  Overall Change: {summary['overall_change_percent']:+.1f}%")

    if summary['degraded'] > 0:
        print(f"\n{'='*60}")
        print("DEGRADED ENDPOINTS")
        print(f"{'='*60}\n")

        for comp in comparisons:
            if comp.status == "degraded":
                print(f"  ⚠️  {comp.endpoint}")
                print(f"     Avg: {comp.baseline_avg:.0f}ms → {comp.current_avg:.0f}ms ({comp.change_percent:+.1f}%)")
                print(f"     P95: {comp.baseline_p95:.0f}ms → {comp.current_p95:.0f}ms ({comp.p95_change_percent:+.1f}%)")

    # Generate report
    output_path = Path(args.results_dir) / f"comparison_{args.current}.md"
    comparator.generate_report(baseline, current, str(output_path))
    print(f"\nComparison report: {output_path}")
    print()


def cmd_validate(args):
    """Validate results against thresholds."""
    analyzer = LoadTestAnalyzer(args.results_dir)

    try:
        results = analyzer.parse_results(args.prefix)
    except Exception as e:
        print(f"Error parsing results: {e}")
        sys.exit(1)

    # Load thresholds
    with open(args.thresholds, 'r') as f:
        thresholds = json.load(f)

    validations = analyzer.validate_thresholds(results, thresholds)

    print(f"\n{'='*60}")
    print("THRESHOLD VALIDATION")
    print(f"{'='*60}\n")

    all_passed = True
    for endpoint, (passed, message) in validations.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {endpoint}")
        print(f"     {message}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("All thresholds passed! ✅")
        sys.exit(0)
    else:
        print("Some thresholds failed! ❌")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze load test results",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--results-dir', '-d',
        default='./reports',
        help='Directory containing result files'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze test results')
    analyze_parser.add_argument('prefix', help='Result file prefix')
    analyze_parser.add_argument(
        '--output', '-o',
        choices=['json', 'markdown', 'html', 'all'],
        default='all',
        help='Output format'
    )

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two test runs')
    compare_parser.add_argument('baseline', help='Baseline result prefix')
    compare_parser.add_argument('current', help='Current result prefix')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate against thresholds')
    validate_parser.add_argument('prefix', help='Result file prefix')
    validate_parser.add_argument(
        '--thresholds', '-t',
        required=True,
        help='JSON file with thresholds'
    )

    args = parser.parse_args()

    if args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'compare':
        cmd_compare(args)
    elif args.command == 'validate':
        cmd_validate(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
