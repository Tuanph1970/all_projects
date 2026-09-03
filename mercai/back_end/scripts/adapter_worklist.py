#!/usr/bin/env python3
"""
Which adapter should I write next?

Answers it from evidence rather than from a guess, which is the loop that
docs/ai-features/05-price-intelligence.md section 12 asks for. Two signals, and
they mean different things:

  UNSUPPORTED DEMAND   hosts sellers pasted and we refused. Pure product
                       signal: every row is someone who wanted a comparison we
                       could not give them. Ranked by DISTINCT SELLERS first,
                       because twelve sellers asking once beats one seller
                       asking forty times -- an adapter serves a market, not a
                       person.

  FAILING SUPPORTED    hosts on the allowlist whose fetches are not returning
                       `ok`. These are adapters that need fixing, not writing,
                       and the status tells you which kind of fixing:
                         js_required    -> the ladder is out of rungs there;
                                          needs an adapter state_path, or the
                                          host is genuinely browser-only
                         no_price_found -> markup changed, or wrong page type
                         blocked_robots -> stop; that is the operator's answer
                         http_error     -> transient, or we are being throttled

Adding a source is a YAML file under services/intel/app/adapters/, so acting on
the top line of this report is usually minutes of work. Choosing the line is
the part that was previously unaided.

    docker exec mercai_intel_service python /app/scripts/adapter_worklist.py
    docker exec mercai_intel_service python /app/scripts/adapter_worklist.py --json
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "intel"))

from shared.database import SessionLocal, engine  # noqa: E402

engine.echo = False
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from app.services import demand  # noqa: E402


def _when(value):
    return value.strftime("%Y-%m-%d") if value else "-"


def render(report):
    supported = report["supported_hosts"]
    print("\nSupported hosts (adapters + INTEL_ALLOWED_HOSTS)")
    print("  " + (", ".join(supported) if supported else "none"))

    rows = report["unsupported_demand"]
    print("\nUnsupported hosts sellers asked for")
    if not rows:
        # Genuinely ambiguous, so say both readings rather than imply success.
        print("  none recorded -- either the allowlist covers what sellers")
        print("  paste, or nobody has tried since this counter shipped.")
    else:
        print(f"  {'host':<32} {'sellers':>7} {'tries':>6}  {'first':<11} {'last':<11}")
        for row in rows:
            print(f"  {row['host'][:32]:<32} {row['sellers']:>7} {row['attempts']:>6}  "
                  f"{_when(row['first_seen']):<11} {_when(row['last_seen']):<11}")
        print("\n  A sample URL for each, to test the ladder against:")
        for row in rows:
            if row["sample_url"]:
                print(f"    {row['host']}: {row['sample_url']}")
        print("\n  Then: python3 back_end/scripts/spike_price_sources.py --urls <file>")

    rows = report["failing_supported"]
    print("\nSupported hosts that are failing")
    if not rows:
        print("  none -- every observation on an allowlisted host returned ok.")
    else:
        print(f"  {'host':<28} {'status':<16} {'n':>6}  {'last':<11}")
        for row in rows:
            print(f"  {row['host'][:28]:<28} {row['status']:<16} {row['count']:>6}  "
                  f"{_when(row['last_seen']):<11}")
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--json", action="store_true",
                        help="machine-readable, for piping somewhere else")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = demand.worklist(db)
    finally:
        db.close()

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        render(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
