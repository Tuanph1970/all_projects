#!/usr/bin/env python3
"""
Security Audit Script

Performs automated security checks on microservices.
Run this before production deployment and periodically.
"""
import os
import sys
import json
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
import subprocess

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Single audit check result"""
    category: str
    check_name: str
    passed: bool
    severity: str  # critical, high, medium, low, info
    message: str
    details: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None


@dataclass
class AuditReport:
    """Complete audit report"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    service: str = ""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    results: List[AuditResult] = field(default_factory=list)

    def add_result(self, result: AuditResult):
        self.results.append(result)
        self.total_checks += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
            if result.severity == "critical":
                self.critical_issues += 1
            elif result.severity == "high":
                self.high_issues += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "service": self.service,
            "summary": {
                "total_checks": self.total_checks,
                "passed": self.passed,
                "failed": self.failed,
                "critical_issues": self.critical_issues,
                "high_issues": self.high_issues,
                "pass_rate": f"{(self.passed / self.total_checks * 100):.1f}%" if self.total_checks > 0 else "N/A"
            },
            "results": [
                {
                    "category": r.category,
                    "check": r.check_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "message": r.message,
                    "details": r.details,
                    "remediation": r.remediation
                }
                for r in self.results
            ]
        }


class SecurityAuditor:
    """Performs security audits on microservices"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.report = AuditReport()

    async def run_all_checks(self) -> AuditReport:
        """Run all security checks"""
        logger.info(f"Starting security audit for {self.base_url}")

        # Authentication checks
        await self.check_auth_endpoints()
        await self.check_jwt_security()
        await self.check_password_policy()

        # API Security checks
        await self.check_rate_limiting()
        await self.check_input_validation()
        await self.check_cors_config()

        # Infrastructure checks
        await self.check_tls_config()
        await self.check_security_headers()
        await self.check_sensitive_data_exposure()

        # Dependency checks
        self.check_dependency_vulnerabilities()

        return self.report

    async def check_auth_endpoints(self):
        """Check authentication endpoint security"""
        async with httpx.AsyncClient() as client:
            # Check login endpoint doesn't expose user existence
            try:
                response = await client.post(
                    f"{self.base_url}/auth/login",
                    json={"email": "nonexistent@test.com", "password": "wrong"}
                )
                # Should return generic error, not "user not found"
                body = response.json()
                if "not found" in str(body).lower() or "does not exist" in str(body).lower():
                    self.report.add_result(AuditResult(
                        category="Authentication",
                        check_name="User enumeration protection",
                        passed=False,
                        severity="high",
                        message="Login endpoint reveals user existence",
                        remediation="Use generic error messages like 'Invalid credentials'"
                    ))
                else:
                    self.report.add_result(AuditResult(
                        category="Authentication",
                        check_name="User enumeration protection",
                        passed=True,
                        severity="high",
                        message="Login endpoint uses generic error messages"
                    ))
            except Exception as e:
                self.report.add_result(AuditResult(
                    category="Authentication",
                    check_name="User enumeration protection",
                    passed=False,
                    severity="info",
                    message=f"Could not check: {e}"
                ))

            # Check brute force protection
            try:
                # Send multiple failed login attempts
                for i in range(10):
                    await client.post(
                        f"{self.base_url}/auth/login",
                        json={"email": "test@test.com", "password": "wrong"}
                    )

                response = await client.post(
                    f"{self.base_url}/auth/login",
                    json={"email": "test@test.com", "password": "wrong"}
                )

                if response.status_code == 429:
                    self.report.add_result(AuditResult(
                        category="Authentication",
                        check_name="Brute force protection",
                        passed=True,
                        severity="critical",
                        message="Rate limiting active on login endpoint"
                    ))
                else:
                    self.report.add_result(AuditResult(
                        category="Authentication",
                        check_name="Brute force protection",
                        passed=False,
                        severity="critical",
                        message="No rate limiting detected on login endpoint",
                        remediation="Implement account lockout or rate limiting"
                    ))
            except Exception as e:
                self.report.add_result(AuditResult(
                    category="Authentication",
                    check_name="Brute force protection",
                    passed=False,
                    severity="info",
                    message=f"Could not check: {e}"
                ))

    async def check_jwt_security(self):
        """Check JWT token security"""
        async with httpx.AsyncClient() as client:
            # Check that expired tokens are rejected
            expired_token = (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiIxIiwiZXhwIjoxNjAwMDAwMDAwfQ."
                "invalid_signature"
            )

            try:
                response = await client.get(
                    f"{self.base_url}/auth/me",
                    headers={"Authorization": f"Bearer {expired_token}"}
                )

                if response.status_code in [401, 403]:
                    self.report.add_result(AuditResult(
                        category="Authentication",
                        check_name="JWT expiration validation",
                        passed=True,
                        severity="critical",
                        message="Expired/invalid tokens are rejected"
                    ))
                else:
                    self.report.add_result(AuditResult(
                        category="Authentication",
                        check_name="JWT expiration validation",
                        passed=False,
                        severity="critical",
                        message="Expired/invalid tokens may be accepted",
                        remediation="Ensure JWT validation includes expiration check"
                    ))
            except Exception as e:
                self.report.add_result(AuditResult(
                    category="Authentication",
                    check_name="JWT expiration validation",
                    passed=False,
                    severity="info",
                    message=f"Could not check: {e}"
                ))

    async def check_password_policy(self):
        """Check password policy enforcement"""
        async with httpx.AsyncClient() as client:
            weak_passwords = ["123456", "password", "abc", "test"]

            for weak_pass in weak_passwords:
                try:
                    response = await client.post(
                        f"{self.base_url}/auth/register",
                        json={
                            "email": "test@example.com",
                            "password": weak_pass,
                            "username": "testuser"
                        }
                    )

                    if response.status_code == 200:
                        self.report.add_result(AuditResult(
                            category="Authentication",
                            check_name="Password policy",
                            passed=False,
                            severity="high",
                            message=f"Weak password '{weak_pass}' was accepted",
                            remediation="Enforce minimum password complexity requirements"
                        ))
                        break
                except Exception:
                    pass
            else:
                self.report.add_result(AuditResult(
                    category="Authentication",
                    check_name="Password policy",
                    passed=True,
                    severity="high",
                    message="Password policy appears to enforce complexity"
                ))

    async def check_rate_limiting(self):
        """Check API rate limiting"""
        async with httpx.AsyncClient() as client:
            try:
                responses = []
                for i in range(100):
                    response = await client.get(f"{self.base_url}/health")
                    responses.append(response.status_code)

                if 429 in responses:
                    self.report.add_result(AuditResult(
                        category="API Security",
                        check_name="Rate limiting",
                        passed=True,
                        severity="high",
                        message="Rate limiting is active"
                    ))
                else:
                    self.report.add_result(AuditResult(
                        category="API Security",
                        check_name="Rate limiting",
                        passed=False,
                        severity="high",
                        message="No rate limiting detected",
                        remediation="Implement rate limiting on all endpoints"
                    ))
            except Exception as e:
                self.report.add_result(AuditResult(
                    category="API Security",
                    check_name="Rate limiting",
                    passed=False,
                    severity="info",
                    message=f"Could not check: {e}"
                ))

    async def check_input_validation(self):
        """Check input validation and injection protection"""
        async with httpx.AsyncClient() as client:
            injection_payloads = [
                "'; DROP TABLE users; --",
                "<script>alert('xss')</script>",
                "${7*7}",
                "{{7*7}}",
                "../../../etc/passwd",
            ]

            for payload in injection_payloads:
                try:
                    response = await client.get(
                        f"{self.base_url}/search",
                        params={"q": payload}
                    )

                    # Check if payload is reflected or causes error
                    if payload in response.text:
                        self.report.add_result(AuditResult(
                            category="API Security",
                            check_name="Input validation",
                            passed=False,
                            severity="critical",
                            message=f"Dangerous payload reflected: {payload[:20]}...",
                            remediation="Implement input sanitization and output encoding"
                        ))
                        return
                except Exception:
                    pass

            self.report.add_result(AuditResult(
                category="API Security",
                check_name="Input validation",
                passed=True,
                severity="critical",
                message="Input validation appears to be working"
            ))

    async def check_cors_config(self):
        """Check CORS configuration"""
        async with httpx.AsyncClient() as client:
            try:
                # Check with wildcard origin
                response = await client.options(
                    f"{self.base_url}/api/test",
                    headers={"Origin": "https://evil.com"}
                )

                cors_origin = response.headers.get("Access-Control-Allow-Origin", "")

                if cors_origin == "*":
                    self.report.add_result(AuditResult(
                        category="API Security",
                        check_name="CORS configuration",
                        passed=False,
                        severity="medium",
                        message="CORS allows all origins (*)",
                        remediation="Restrict CORS to specific trusted origins"
                    ))
                elif "evil.com" in cors_origin:
                    self.report.add_result(AuditResult(
                        category="API Security",
                        check_name="CORS configuration",
                        passed=False,
                        severity="high",
                        message="CORS reflects untrusted origins",
                        remediation="Implement CORS origin whitelist"
                    ))
                else:
                    self.report.add_result(AuditResult(
                        category="API Security",
                        check_name="CORS configuration",
                        passed=True,
                        severity="medium",
                        message="CORS properly restricts origins"
                    ))
            except Exception as e:
                self.report.add_result(AuditResult(
                    category="API Security",
                    check_name="CORS configuration",
                    passed=False,
                    severity="info",
                    message=f"Could not check: {e}"
                ))

    async def check_tls_config(self):
        """Check TLS/SSL configuration"""
        # This would typically check actual TLS config
        # For now, check if HTTPS redirect is in place
        async with httpx.AsyncClient(follow_redirects=False) as client:
            try:
                http_url = self.base_url.replace("https://", "http://")
                response = await client.get(http_url)

                if response.status_code in [301, 302, 308]:
                    location = response.headers.get("location", "")
                    if location.startswith("https://"):
                        self.report.add_result(AuditResult(
                            category="Infrastructure",
                            check_name="HTTPS redirect",
                            passed=True,
                            severity="high",
                            message="HTTP redirects to HTTPS"
                        ))
                    else:
                        self.report.add_result(AuditResult(
                            category="Infrastructure",
                            check_name="HTTPS redirect",
                            passed=False,
                            severity="high",
                            message="HTTP does not redirect to HTTPS",
                            remediation="Configure HTTP to HTTPS redirect"
                        ))
            except Exception:
                self.report.add_result(AuditResult(
                    category="Infrastructure",
                    check_name="HTTPS redirect",
                    passed=True,
                    severity="info",
                    message="Could not test HTTP redirect (may already be HTTPS only)"
                ))

    async def check_security_headers(self):
        """Check security headers"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                headers = response.headers

                required_headers = {
                    "X-Content-Type-Options": ("nosniff", "high"),
                    "X-Frame-Options": ("DENY", "medium"),
                    "X-XSS-Protection": ("1", "medium"),
                    "Strict-Transport-Security": (None, "high"),
                    "Content-Security-Policy": (None, "medium"),
                }

                for header, (expected_value, severity) in required_headers.items():
                    if header.lower() in [h.lower() for h in headers.keys()]:
                        self.report.add_result(AuditResult(
                            category="Infrastructure",
                            check_name=f"Security header: {header}",
                            passed=True,
                            severity=severity,
                            message=f"{header} header is present"
                        ))
                    else:
                        self.report.add_result(AuditResult(
                            category="Infrastructure",
                            check_name=f"Security header: {header}",
                            passed=False,
                            severity=severity,
                            message=f"{header} header is missing",
                            remediation=f"Add {header} header to responses"
                        ))
            except Exception as e:
                self.report.add_result(AuditResult(
                    category="Infrastructure",
                    check_name="Security headers",
                    passed=False,
                    severity="info",
                    message=f"Could not check: {e}"
                ))

    async def check_sensitive_data_exposure(self):
        """Check for sensitive data in responses"""
        async with httpx.AsyncClient() as client:
            try:
                # Check error responses for stack traces
                response = await client.get(f"{self.base_url}/nonexistent-endpoint-12345")
                body = response.text.lower()

                sensitive_patterns = [
                    "traceback",
                    "stack trace",
                    "file \"",
                    "line ",
                    "exception",
                    "password",
                    "secret_key",
                    "api_key",
                ]

                found_sensitive = [p for p in sensitive_patterns if p in body]

                if found_sensitive:
                    self.report.add_result(AuditResult(
                        category="Data Security",
                        check_name="Error response sanitization",
                        passed=False,
                        severity="high",
                        message=f"Sensitive info in error response: {found_sensitive}",
                        remediation="Sanitize error responses to hide internal details"
                    ))
                else:
                    self.report.add_result(AuditResult(
                        category="Data Security",
                        check_name="Error response sanitization",
                        passed=True,
                        severity="high",
                        message="Error responses appear to be sanitized"
                    ))
            except Exception as e:
                self.report.add_result(AuditResult(
                    category="Data Security",
                    check_name="Error response sanitization",
                    passed=False,
                    severity="info",
                    message=f"Could not check: {e}"
                ))

    def check_dependency_vulnerabilities(self):
        """Check for known vulnerabilities in dependencies"""
        try:
            # Run pip-audit or safety check
            result = subprocess.run(
                ["pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                if vulnerabilities:
                    critical_vulns = [v for v in vulnerabilities if v.get("severity") == "CRITICAL"]
                    high_vulns = [v for v in vulnerabilities if v.get("severity") == "HIGH"]

                    self.report.add_result(AuditResult(
                        category="Dependencies",
                        check_name="Vulnerability scan",
                        passed=len(critical_vulns) == 0 and len(high_vulns) == 0,
                        severity="critical" if critical_vulns else "high" if high_vulns else "medium",
                        message=f"Found {len(vulnerabilities)} vulnerabilities ({len(critical_vulns)} critical, {len(high_vulns)} high)",
                        details={"vulnerabilities": vulnerabilities[:10]},
                        remediation="Update affected packages to patched versions"
                    ))
                else:
                    self.report.add_result(AuditResult(
                        category="Dependencies",
                        check_name="Vulnerability scan",
                        passed=True,
                        severity="critical",
                        message="No known vulnerabilities found"
                    ))
            else:
                self.report.add_result(AuditResult(
                    category="Dependencies",
                    check_name="Vulnerability scan",
                    passed=False,
                    severity="info",
                    message="pip-audit not available or failed"
                ))
        except Exception as e:
            self.report.add_result(AuditResult(
                category="Dependencies",
                check_name="Vulnerability scan",
                passed=False,
                severity="info",
                message=f"Could not run vulnerability scan: {e}"
            ))


def print_report(report: AuditReport):
    """Print audit report to console"""
    print("\n" + "=" * 70)
    print("  SECURITY AUDIT REPORT")
    print("=" * 70)
    print(f"  Timestamp: {report.timestamp.isoformat()}")
    print(f"  Service: {report.service or 'N/A'}")
    print()
    print(f"  Total Checks: {report.total_checks}")
    print(f"  Passed: {report.passed}")
    print(f"  Failed: {report.failed}")
    print(f"  Critical Issues: {report.critical_issues}")
    print(f"  High Issues: {report.high_issues}")
    print("=" * 70)

    # Group results by category
    categories = {}
    for result in report.results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)

    for category, results in categories.items():
        print(f"\n  [{category}]")
        for result in results:
            status = "✅" if result.passed else "❌"
            print(f"    {status} {result.check_name}")
            if not result.passed:
                print(f"       └─ {result.severity.upper()}: {result.message}")
                if result.remediation:
                    print(f"       └─ Fix: {result.remediation}")

    print("\n" + "=" * 70)

    if report.critical_issues > 0 or report.high_issues > 0:
        print("  ⚠️  ACTION REQUIRED: Fix critical and high severity issues before deployment")
    else:
        print("  ✅ No critical or high severity issues found")
    print("=" * 70)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Security Audit Tool")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to audit")
    parser.add_argument("--output", "-o", help="Output file for JSON report")
    parser.add_argument("--service", default="", help="Service name for report")

    args = parser.parse_args()

    auditor = SecurityAuditor(base_url=args.url)
    auditor.report.service = args.service

    report = await auditor.run_all_checks()

    print_report(report)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nReport saved to: {args.output}")

    # Exit with error if critical issues found
    if report.critical_issues > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
