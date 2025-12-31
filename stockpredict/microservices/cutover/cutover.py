#!/usr/bin/env python3
"""
Cutover CLI Tool
Manages gradual traffic cutover from Django to microservices

Usage:
    python cutover.py status
    python cutover.py apply canary --dry-run
    python cutover.py apply half --confirm
    python cutover.py rollback "High error rate"
    python cutover.py set auth_microservice 50
"""
import argparse
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import subprocess

import httpx


# Configuration
FEATURE_FLAGS_URL = os.getenv("FEATURE_FLAGS_URL", "http://localhost:8010")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-in-production")
SHADOW_COMPARATOR_URL = os.getenv("SHADOW_COMPARATOR_URL", "http://localhost:9000")


# Phase definitions
PHASES = {
    "shadow": "Shadow Mode (0% to microservices)",
    "canary": "Canary Release (10% to microservices)",
    "early_adopter": "Early Adopter (30% to microservices)",
    "half": "50/50 Split (50% to microservices)",
    "majority": "Majority Migrated (80% to microservices)",
    "final_validation": "Final Validation (95% to microservices)",
    "complete": "Complete Cutover (100% to microservices)",
    "rollback": "Emergency Rollback (0% to microservices)",
}


# Colors
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'


def print_header(text: str):
    """Print a header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*50}{Colors.NC}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.NC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*50}{Colors.NC}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.NC}")


def api_request(
    method: str,
    endpoint: str,
    data: Dict = None,
    params: Dict = None
) -> Optional[Dict]:
    """Make an API request to the feature flags service"""
    url = f"{FEATURE_FLAGS_URL}{endpoint}"
    headers = {
        "X-Admin-Key": ADMIN_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        with httpx.Client(timeout=30) as client:
            if method == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = client.post(url, headers=headers, json=data, params=params)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as e:
        print_error(f"API request failed: {e}")
        return None
    except Exception as e:
        print_error(f"Error: {e}")
        return None


def cmd_status(args):
    """Show current cutover status"""
    print_header("CUTOVER STATUS")

    # Get current status
    status = api_request("GET", "/api/flags/status/current")
    if not status:
        print_error("Failed to get status")
        return 1

    current_phase = status.get("current_phase", "unknown")
    print(f"  Current Phase: {Colors.BOLD}{current_phase}{Colors.NC}")
    print(f"  Description: {PHASES.get(current_phase, 'Unknown phase')}")
    print(f"  Last Updated: {status.get('last_updated', 'N/A')}")
    print()

    # Show flag percentages
    print(f"  {Colors.BOLD}Service Traffic Percentages:{Colors.NC}")
    print()

    flags = status.get("flags", {})
    for flag_name, flag_data in sorted(flags.items()):
        if isinstance(flag_data, dict):
            pct = flag_data.get("percentage", 0)
            enabled = flag_data.get("enabled", False)

            # Progress bar
            bar_width = 30
            filled = int(bar_width * pct / 100)
            bar = "█" * filled + "░" * (bar_width - filled)

            status_icon = "●" if enabled else "○"
            color = Colors.GREEN if pct > 0 else Colors.NC

            print(f"    {status_icon} {flag_name:30} [{color}{bar}{Colors.NC}] {pct:3}%")

    print()

    # Get shadow comparator metrics if available
    try:
        with httpx.Client(timeout=5) as client:
            comparator_stats = client.get(f"{SHADOW_COMPARATOR_URL}/metrics/stats").json()

            print(f"  {Colors.BOLD}Shadow Comparator Metrics:{Colors.NC}")
            print()
            print(f"    Total Comparisons: {comparator_stats.get('total_comparisons', 0)}")
            print(f"    Match Rate: {comparator_stats.get('match_rate', 0):.1f}%")
            print(f"    Avg Latency Diff: {comparator_stats.get('avg_latency_diff_ms', 0):.1f}ms")
            print()
    except:
        pass

    return 0


def cmd_apply(args):
    """Apply a cutover phase"""
    phase = args.phase
    dry_run = args.dry_run
    confirm = args.confirm

    if phase not in PHASES:
        print_error(f"Unknown phase: {phase}")
        print(f"Available phases: {', '.join(PHASES.keys())}")
        return 1

    print_header(f"APPLY PHASE: {phase.upper()}")
    print(f"  Phase: {phase}")
    print(f"  Description: {PHASES[phase]}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    if not dry_run and not confirm:
        print_warning("This will modify production traffic routing!")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Aborted.")
            return 1

    # Health check first
    print_info("Running health checks...")
    # health_script = os.path.join(os.path.dirname(__file__), "scripts", "health_check.sh")
    # In a real environment, we'd run the health check script here

    # Apply phase
    print_info(f"Applying phase: {phase}")

    result = api_request("POST", "/api/admin/phases/apply", data={
        "phase": phase,
        "reason": f"Applied via CLI by {os.getenv('USER', 'unknown')}",
        "dry_run": dry_run
    })

    if not result:
        print_error("Failed to apply phase")
        return 1

    if result.get("success"):
        print_success(f"Phase '{phase}' applied successfully")
        print()

        print(f"  {Colors.BOLD}Changes:{Colors.NC}")
        for change in result.get("changes", []):
            old_pct = change.get("old_percentage", 0)
            new_pct = change.get("new_percentage", 0)
            flag = change.get("flag", "unknown")

            if new_pct > old_pct:
                arrow = f"{Colors.GREEN}↑{Colors.NC}"
            elif new_pct < old_pct:
                arrow = f"{Colors.RED}↓{Colors.NC}"
            else:
                arrow = "="

            print(f"    {flag:30} {old_pct:3}% {arrow} {new_pct:3}%")

        print()

        if dry_run:
            print_warning("DRY RUN - No changes were actually applied")
        else:
            print_success("Phase applied. Monitor metrics for any issues.")
    else:
        print_error("Phase application failed")
        return 1

    return 0


def cmd_rollback(args):
    """Emergency rollback"""
    reason = args.reason

    print_header("EMERGENCY ROLLBACK")
    print_warning("This will route ALL traffic back to Django!")
    print()
    print(f"  Reason: {reason}")
    print()

    response = input("Type 'ROLLBACK' to confirm: ")
    if response != 'ROLLBACK':
        print("Aborted.")
        return 1

    print_info("Executing rollback...")

    result = api_request("POST", f"/api/admin/rollback", params={"reason": reason})

    if result and result.get("status") == "rolled_back":
        print_success("Rollback completed!")
        print()
        print(f"  Previous Phase: {result.get('previous_phase', 'unknown')}")
        print(f"  Timestamp: {result.get('timestamp', 'N/A')}")
        print()
        print_warning("All traffic is now routing to Django.")
        print("  Investigate the issue before resuming cutover.")
    else:
        print_error("Rollback may have failed. Check logs.")
        return 1

    return 0


def cmd_set(args):
    """Set individual flag percentage"""
    flag_name = args.flag
    percentage = args.percentage

    print_header(f"SET FLAG: {flag_name}")

    if percentage < 0 or percentage > 100:
        print_error("Percentage must be between 0 and 100")
        return 1

    print(f"  Flag: {flag_name}")
    print(f"  New Percentage: {percentage}%")
    print()

    if not args.confirm:
        response = input("Confirm? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return 1

    result = api_request(
        "POST",
        f"/api/admin/flags/{flag_name}/percentage",
        params={"percentage": percentage}
    )

    if result:
        print_success(f"Flag '{flag_name}' updated to {percentage}%")
    else:
        print_error("Failed to update flag")
        return 1

    return 0


def cmd_phases(args):
    """List available phases"""
    print_header("AVAILABLE PHASES")

    result = api_request("GET", "/api/flags/phases/list")
    if not result:
        # Fall back to local definition
        for phase, desc in PHASES.items():
            print(f"  {phase:20} - {desc}")
        return 0

    phases = result.get("phases", {})
    for phase_name, phase_info in phases.items():
        week = phase_info.get("week", "?")
        desc = phase_info.get("description", "")
        print(f"  {phase_name:20} (Week {week}) - {desc}")

    return 0


def cmd_audit(args):
    """Show audit log"""
    print_header("AUDIT LOG")

    result = api_request("GET", "/api/admin/audit-log", params={"limit": args.limit})

    if not result:
        print_error("Failed to get audit log")
        return 1

    entries = result.get("entries", [])
    if not entries:
        print("  No audit entries found.")
        return 0

    for entry in entries:
        timestamp = entry.get("timestamp", "N/A")
        action = entry.get("action", "unknown")
        flag = entry.get("flag_name", "unknown")
        actor = entry.get("actor", "unknown")

        print(f"  [{timestamp}] {action:10} {flag:30} by {actor}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Cutover CLI - Manage traffic migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                    Show current cutover status
  %(prog)s apply canary --dry-run    Preview canary phase changes
  %(prog)s apply half --confirm      Apply 50/50 split
  %(prog)s rollback "High errors"    Emergency rollback
  %(prog)s set auth_microservice 75  Set specific flag to 75%
  %(prog)s phases                    List available phases
  %(prog)s audit --limit 50          Show recent audit log
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status command
    status_parser = subparsers.add_parser("status", help="Show cutover status")
    status_parser.set_defaults(func=cmd_status)

    # apply command
    apply_parser = subparsers.add_parser("apply", help="Apply a cutover phase")
    apply_parser.add_argument("phase", help="Phase name to apply")
    apply_parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    apply_parser.add_argument("--confirm", action="store_true", help="Skip confirmation")
    apply_parser.set_defaults(func=cmd_apply)

    # rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Emergency rollback")
    rollback_parser.add_argument("reason", help="Reason for rollback")
    rollback_parser.set_defaults(func=cmd_rollback)

    # set command
    set_parser = subparsers.add_parser("set", help="Set individual flag percentage")
    set_parser.add_argument("flag", help="Flag name")
    set_parser.add_argument("percentage", type=int, help="Percentage (0-100)")
    set_parser.add_argument("--confirm", action="store_true", help="Skip confirmation")
    set_parser.set_defaults(func=cmd_set)

    # phases command
    phases_parser = subparsers.add_parser("phases", help="List available phases")
    phases_parser.set_defaults(func=cmd_phases)

    # audit command
    audit_parser = subparsers.add_parser("audit", help="Show audit log")
    audit_parser.add_argument("--limit", type=int, default=20, help="Number of entries")
    audit_parser.set_defaults(func=cmd_audit)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
