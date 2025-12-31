#!/usr/bin/env python3
"""
Migration Orchestrator
Runs all migration scripts in the correct order

Usage:
    python run_migration.py --mode dry_run
    python run_migration.py --mode initial --confirm
    python run_migration.py --verify
"""
import argparse
import subprocess
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
import json


# Migration script order
MIGRATION_SCRIPTS = [
    ("migrate_users.py", "Users & Profiles"),
    ("migrate_stock_data.py", "Companies & Stock Data"),
]

# Legacy scripts (if they exist)
LEGACY_MIGRATION_SCRIPTS = [
    ("001_migrate_users.py", "Users"),
    ("002_migrate_companies.py", "Companies & Stock Data"),
    ("003_migrate_portfolios.py", "Portfolios & Holdings"),
    ("004_migrate_transactions.py", "Transactions"),
]


def run_script(script_name: str, mode: str, extra_args: List[str] = None) -> Dict[str, Any]:
    """Run a migration script and capture results"""
    script_path = os.path.join(os.path.dirname(__file__), "scripts", script_name)

    cmd = [sys.executable, script_path, "--mode", mode]
    if extra_args:
        cmd.extend(extra_args)

    start_time = datetime.utcnow()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        return {
            "script": script_name,
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "return_code": result.returncode,
            "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
        }

    except subprocess.TimeoutExpired:
        return {
            "script": script_name,
            "success": False,
            "output": "",
            "errors": "Script timed out after 1 hour",
            "return_code": -1,
            "duration_seconds": 3600
        }
    except Exception as e:
        return {
            "script": script_name,
            "success": False,
            "output": "",
            "errors": str(e),
            "return_code": -1,
            "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
        }


def run_verification() -> Dict[str, Any]:
    """Run verification script"""
    verify_path = os.path.join(os.path.dirname(__file__), "verify", "verify_migration.py")

    result = subprocess.run(
        [sys.executable, verify_path, "--full"],
        capture_output=True,
        text=True
    )

    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "errors": result.stderr
    }


def main():
    parser = argparse.ArgumentParser(description="Run all migrations")
    parser.add_argument(
        "--mode",
        choices=["dry_run", "initial", "incremental"],
        default="dry_run",
        help="Migration mode"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for non-dry-run modes"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run verification after migration"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run verification"
    )
    parser.add_argument(
        "--script",
        help="Run specific script only"
    )
    parser.add_argument(
        "--output",
        help="Save results to JSON file"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("migration")

    # Safety check
    if args.mode != "dry_run" and not args.confirm:
        print("❌ Non-dry-run modes require --confirm flag")
        print("   This is a safety measure to prevent accidental data changes")
        sys.exit(1)

    if args.verify_only:
        print("\n=== Running Verification Only ===\n")
        result = run_verification()
        print(result["output"])
        if result["errors"]:
            print(result["errors"])
        sys.exit(0 if result["success"] else 1)

    # Print banner
    print("\n" + "=" * 60)
    print("  STOCK HELPER - DATA MIGRATION")
    print("=" * 60)
    print(f"  Mode: {args.mode.upper()}")
    print(f"  Started: {datetime.utcnow().isoformat()}")
    print("=" * 60 + "\n")

    if args.mode == "dry_run":
        print("⚠️  DRY RUN - No data will be modified\n")

    results = {
        "started_at": datetime.utcnow().isoformat(),
        "mode": args.mode,
        "scripts": [],
        "verification": None
    }

    # Filter scripts if specific one requested
    scripts_to_run = MIGRATION_SCRIPTS
    if args.script:
        scripts_to_run = [
            (s, d) for s, d in MIGRATION_SCRIPTS
            if args.script in s
        ]
        if not scripts_to_run:
            print(f"❌ Script not found: {args.script}")
            sys.exit(1)

    # Run migrations
    all_success = True
    for script_name, description in scripts_to_run:
        print(f"\n{'='*40}")
        print(f"  {description}")
        print(f"  Script: {script_name}")
        print(f"{'='*40}\n")

        result = run_script(script_name, args.mode)
        results["scripts"].append(result)

        # Print output
        if result["output"]:
            print(result["output"])

        if not result["success"]:
            all_success = False
            print(f"\n❌ Script failed: {script_name}")
            if result["errors"]:
                print(f"Errors: {result["errors"]}")

            # Stop on failure for non-dry-run
            if args.mode != "dry_run":
                print("\n🛑 Stopping migration due to failure")
                break

    # Run verification if requested
    if args.verify and all_success:
        print("\n" + "=" * 40)
        print("  VERIFICATION")
        print("=" * 40 + "\n")

        verification = run_verification()
        results["verification"] = verification
        print(verification["output"])

    # Summary
    print("\n" + "=" * 60)
    print("  MIGRATION SUMMARY")
    print("=" * 60)

    total_scripts = len(results["scripts"])
    successful = sum(1 for r in results["scripts"] if r["success"])
    failed = total_scripts - successful

    print(f"  Scripts Run: {total_scripts}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    total_duration = sum(r["duration_seconds"] for r in results["scripts"])
    print(f"  Total Duration: {total_duration:.2f}s")

    if failed > 0:
        print("\n  ❌ MIGRATION INCOMPLETE - Some scripts failed")
    else:
        print("\n  ✓ MIGRATION COMPLETE")

    # Save results
    if args.output:
        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = failed == 0

        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to: {args.output}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
