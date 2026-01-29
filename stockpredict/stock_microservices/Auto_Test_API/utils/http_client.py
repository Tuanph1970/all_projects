"""
HTTP Client utilities for API testing
"""
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import json
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class APIResponse:
    """Wrapper for API response"""
    status_code: int
    data: Any
    headers: Dict[str, str]
    elapsed_ms: float
    success: bool = field(init=False)
    error: Optional[str] = None

    def __post_init__(self):
        self.success = 200 <= self.status_code < 300

    def json(self) -> Any:
        return self.data

    def __repr__(self):
        return f"APIResponse(status={self.status_code}, success={self.success})"


class APIClient:
    """API Client for testing"""

    def __init__(self, base_url: str, timeout: int = 30, verbose: bool = True):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    def set_auth_tokens(self, access_token: str, refresh_token: str = None):
        """Set authentication tokens"""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self.session.headers["Authorization"] = f"Bearer {access_token}"

    def clear_auth(self):
        """Clear authentication"""
        self._access_token = None
        self._refresh_token = None
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]

    @property
    def access_token(self) -> Optional[str]:
        return self._access_token

    @property
    def refresh_token(self) -> Optional[str]:
        return self._refresh_token

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint"""
        if endpoint.startswith("http"):
            return endpoint
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details"""
        if self.verbose:
            console.print(f"\n[bold blue]→ {method}[/] {url}")
            if kwargs.get("json"):
                console.print(f"[dim]Body: {json.dumps(kwargs['json'], indent=2)}[/]")
            if kwargs.get("params"):
                console.print(f"[dim]Params: {kwargs['params']}[/]")

    def _log_response(self, response: APIResponse):
        """Log response details"""
        if self.verbose:
            status_color = "green" if response.success else "red"
            console.print(
                f"[bold {status_color}]← {response.status_code}[/] "
                f"({response.elapsed_ms:.0f}ms)"
            )
            if not response.success and response.error:
                console.print(f"[red]Error: {response.error}[/]")
            elif response.data and self.verbose:
                try:
                    data_str = json.dumps(response.data, indent=2, default=str)
                    if len(data_str) > 500:
                        data_str = data_str[:500] + "..."
                    console.print(f"[dim]{data_str}[/]")
                except:
                    pass

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> APIResponse:
        """Make HTTP request"""
        url = self._build_url(endpoint)
        kwargs.setdefault("timeout", self.timeout)

        self._log_request(method, url, **kwargs)

        try:
            response = self.session.request(method, url, **kwargs)
            elapsed_ms = response.elapsed.total_seconds() * 1000

            try:
                data = response.json()
            except:
                data = response.text

            error = None
            if not response.ok:
                if isinstance(data, dict):
                    error = data.get("detail") or data.get("error") or data.get("message")
                else:
                    error = str(data) if data else None

            api_response = APIResponse(
                status_code=response.status_code,
                data=data,
                headers=dict(response.headers),
                elapsed_ms=elapsed_ms,
                error=error
            )

            self._log_response(api_response)
            return api_response

        except requests.exceptions.Timeout:
            return APIResponse(
                status_code=408,
                data=None,
                headers={},
                elapsed_ms=self.timeout * 1000,
                error="Request timeout"
            )
        except requests.exceptions.ConnectionError as e:
            return APIResponse(
                status_code=503,
                data=None,
                headers={},
                elapsed_ms=0,
                error=f"Connection error: {str(e)}"
            )
        except Exception as e:
            return APIResponse(
                status_code=500,
                data=None,
                headers={},
                elapsed_ms=0,
                error=f"Unexpected error: {str(e)}"
            )

    def get(self, endpoint: str, params: Dict = None, **kwargs) -> APIResponse:
        """HTTP GET request"""
        return self._make_request("GET", endpoint, params=params, **kwargs)

    def post(self, endpoint: str, json: Dict = None, data: Dict = None, **kwargs) -> APIResponse:
        """HTTP POST request"""
        return self._make_request("POST", endpoint, json=json, data=data, **kwargs)

    def put(self, endpoint: str, json: Dict = None, **kwargs) -> APIResponse:
        """HTTP PUT request"""
        return self._make_request("PUT", endpoint, json=json, **kwargs)

    def patch(self, endpoint: str, json: Dict = None, **kwargs) -> APIResponse:
        """HTTP PATCH request"""
        return self._make_request("PATCH", endpoint, json=json, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """HTTP DELETE request"""
        return self._make_request("DELETE", endpoint, **kwargs)


def print_test_result(test_name: str, passed: bool, message: str = ""):
    """Print test result"""
    status = "[bold green]✓ PASS[/]" if passed else "[bold red]✗ FAIL[/]"
    console.print(f"{status} {test_name}")
    if message and not passed:
        console.print(f"  [dim]{message}[/]")


def print_section(title: str):
    """Print section header"""
    console.print(f"\n[bold cyan]{'='*60}[/]")
    console.print(f"[bold cyan]{title}[/]")
    console.print(f"[bold cyan]{'='*60}[/]")


def print_summary(passed: int, failed: int, total: int):
    """Print test summary"""
    console.print(f"\n[bold]{'='*60}[/]")
    console.print("[bold]TEST SUMMARY[/]")
    console.print(f"[bold]{'='*60}[/]")

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Tests", str(total))
    table.add_row("Passed", f"[green]{passed}[/]")
    table.add_row("Failed", f"[red]{failed}[/]")
    table.add_row("Success Rate", f"{passed/total*100:.1f}%" if total > 0 else "N/A")

    console.print(table)

    if failed == 0:
        console.print("\n[bold green]All tests passed![/]")
    else:
        console.print(f"\n[bold red]{failed} test(s) failed![/]")
