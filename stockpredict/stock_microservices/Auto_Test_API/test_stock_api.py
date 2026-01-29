#!/usr/bin/env python3
"""
Stock Helper API - Complete Test Suite

This script runs all API tests for the Stock Helper Microservices platform.

Services Tested:
1. Auth Service - User authentication and authorization
2. Stock Data Service - Stock data, companies, market info
3. Portfolio Service - Portfolio management, holdings, transactions
4. Analysis Service - Technical and fundamental analysis
5. Prediction Service - ML-based stock price predictions
6. AI Insights Service - LLM-powered insights
7. Chatbot Service - Conversational AI

Usage:
    python test_stock_api.py                    # Run all tests
    python test_stock_api.py --service auth     # Run only auth tests
    python test_stock_api.py --service stock    # Run only stock data tests
    python test_stock_api.py --quiet            # Run with minimal output
    python test_stock_api.py --base-url http://localhost:8004/stock_helper/api/v2
"""
import sys
import os
import argparse
from datetime import datetime
from typing import Dict, Tuple

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from utils.http_client import print_section, print_summary
from rich.console import Console
from rich.table import Table

# Import test classes
from tests.test_auth_api import TestAuthAPI
from tests.test_stock_data_api import TestStockDataAPI
from tests.test_portfolio_api import TestPortfolioAPI
from tests.test_analysis_api import TestAnalysisAPI
from tests.test_prediction_api import TestPredictionAPI
from tests.test_ai_insights_api import TestAIInsightsAPI
from tests.test_chatbot_api import TestChatbotAPI

console = Console()


class StockAPITestRunner:
    """Main test runner for all API tests"""

    def __init__(self, base_url: str = None, verbose: bool = True):
        self.base_url = base_url or settings.BASE_URL
        self.verbose = verbose
        self.results: Dict[str, Tuple[int, int, int]] = {}

    def run_auth_tests(self) -> Tuple[int, int, int]:
        """Run authentication API tests"""
        tester = TestAuthAPI(base_url=self.base_url, verbose=self.verbose)
        return tester.run_all_tests()

    def run_stock_data_tests(self) -> Tuple[int, int, int]:
        """Run stock data API tests"""
        tester = TestStockDataAPI(base_url=self.base_url, verbose=self.verbose)
        return tester.run_all_tests()

    def run_portfolio_tests(self) -> Tuple[int, int, int]:
        """Run portfolio API tests"""
        tester = TestPortfolioAPI(base_url=self.base_url, verbose=self.verbose)
        return tester.run_all_tests()

    def run_analysis_tests(self) -> Tuple[int, int, int]:
        """Run analysis API tests"""
        tester = TestAnalysisAPI(base_url=self.base_url, verbose=self.verbose)
        return tester.run_all_tests()

    def run_prediction_tests(self) -> Tuple[int, int, int]:
        """Run prediction API tests"""
        tester = TestPredictionAPI(base_url=self.base_url, verbose=self.verbose)
        return tester.run_all_tests()

    def run_ai_insights_tests(self) -> Tuple[int, int, int]:
        """Run AI insights API tests"""
        tester = TestAIInsightsAPI(base_url=self.base_url, verbose=self.verbose)
        return tester.run_all_tests()

    def run_chatbot_tests(self) -> Tuple[int, int, int]:
        """Run chatbot API tests"""
        tester = TestChatbotAPI(base_url=self.base_url, verbose=self.verbose)
        return tester.run_all_tests()

    def run_service_tests(self, service: str) -> Tuple[int, int, int]:
        """Run tests for a specific service"""
        service_map = {
            "auth": self.run_auth_tests,
            "stock": self.run_stock_data_tests,
            "stock-data": self.run_stock_data_tests,
            "portfolio": self.run_portfolio_tests,
            "analysis": self.run_analysis_tests,
            "prediction": self.run_prediction_tests,
            "ai": self.run_ai_insights_tests,
            "ai-insights": self.run_ai_insights_tests,
            "chatbot": self.run_chatbot_tests,
            "chat": self.run_chatbot_tests,
        }

        if service.lower() not in service_map:
            console.print(f"[red]Unknown service: {service}[/]")
            console.print(f"Available services: {', '.join(service_map.keys())}")
            return 0, 1, 1

        return service_map[service.lower()]()

    def run_all_tests(self) -> Dict[str, Tuple[int, int, int]]:
        """Run all API tests"""
        console.print("\n[bold blue]" + "=" * 70 + "[/]")
        console.print("[bold blue]     STOCK HELPER API - COMPLETE TEST SUITE[/]")
        console.print("[bold blue]" + "=" * 70 + "[/]")
        console.print(f"\n[dim]Base URL: {self.base_url}[/]")
        console.print(f"[dim]Started: {datetime.now().isoformat()}[/]")
        console.print()

        # Run tests for each service
        services = [
            ("Authentication", self.run_auth_tests),
            ("Stock Data", self.run_stock_data_tests),
            ("Portfolio", self.run_portfolio_tests),
            ("Analysis", self.run_analysis_tests),
            ("Prediction", self.run_prediction_tests),
            ("AI Insights", self.run_ai_insights_tests),
            ("Chatbot", self.run_chatbot_tests),
        ]

        for service_name, test_func in services:
            try:
                passed, failed, total = test_func()
                self.results[service_name] = (passed, failed, total)
            except Exception as e:
                console.print(f"\n[red]Error running {service_name} tests: {e}[/]")
                self.results[service_name] = (0, 1, 1)

        return self.results

    def print_final_summary(self):
        """Print final test summary"""
        console.print("\n" + "=" * 70)
        console.print("[bold cyan]FINAL TEST SUMMARY[/]")
        console.print("=" * 70 + "\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan")
        table.add_column("Passed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Total", justify="right")
        table.add_column("Rate", justify="right")

        total_passed = 0
        total_failed = 0
        total_tests = 0

        for service, (passed, failed, total) in self.results.items():
            rate = f"{passed/total*100:.1f}%" if total > 0 else "N/A"
            table.add_row(service, str(passed), str(failed), str(total), rate)
            total_passed += passed
            total_failed += failed
            total_tests += total

        table.add_row("", "", "", "", "", style="dim")
        overall_rate = f"{total_passed/total_tests*100:.1f}%" if total_tests > 0 else "N/A"
        table.add_row(
            "[bold]TOTAL[/]",
            f"[bold green]{total_passed}[/]",
            f"[bold red]{total_failed}[/]",
            f"[bold]{total_tests}[/]",
            f"[bold]{overall_rate}[/]"
        )

        console.print(table)

        console.print(f"\n[dim]Completed: {datetime.now().isoformat()}[/]")

        if total_failed == 0:
            console.print("\n[bold green]✓ All tests passed![/]\n")
        else:
            console.print(f"\n[bold red]✗ {total_failed} test(s) failed![/]\n")

        return total_failed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Stock Helper API Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_stock_api.py                          # Run all tests
  python test_stock_api.py --service auth           # Run only auth tests
  python test_stock_api.py --service stock          # Run only stock data tests
  python test_stock_api.py --service portfolio      # Run only portfolio tests
  python test_stock_api.py --service analysis       # Run only analysis tests
  python test_stock_api.py --service prediction     # Run only prediction tests
  python test_stock_api.py --service ai             # Run only AI insights tests
  python test_stock_api.py --service chatbot        # Run only chatbot tests
  python test_stock_api.py --quiet                  # Run with minimal output

Available services: auth, stock, portfolio, analysis, prediction, ai, chatbot
        """
    )

    parser.add_argument(
        "--base-url",
        default=settings.BASE_URL,
        help=f"Base URL for API (default: {settings.BASE_URL})"
    )
    parser.add_argument(
        "--service", "-s",
        help="Run tests for specific service only"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--list-services",
        action="store_true",
        help="List available services"
    )

    args = parser.parse_args()

    if args.list_services:
        console.print("\n[bold]Available services:[/]")
        services = [
            ("auth", "Authentication API - Register, login, tokens"),
            ("stock / stock-data", "Stock Data API - Companies, prices, market data"),
            ("portfolio", "Portfolio API - Portfolios, holdings, transactions"),
            ("analysis", "Analysis API - Technical and fundamental analysis"),
            ("prediction", "Prediction API - ML price predictions"),
            ("ai / ai-insights", "AI Insights API - LLM-powered insights"),
            ("chatbot / chat", "Chatbot API - Conversational AI"),
        ]
        for name, desc in services:
            console.print(f"  [cyan]{name}[/] - {desc}")
        console.print()
        return 0

    runner = StockAPITestRunner(
        base_url=args.base_url,
        verbose=not args.quiet
    )

    if args.service:
        # Run tests for specific service
        passed, failed, total = runner.run_service_tests(args.service)
        return 0 if failed == 0 else 1
    else:
        # Run all tests
        runner.run_all_tests()
        failed = runner.print_final_summary()
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
