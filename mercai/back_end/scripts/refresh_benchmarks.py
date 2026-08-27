#!/usr/bin/env python3
"""
Re-sample the external category benchmarks.

There is still no scheduler in this stack, so this exists to be run by hand or
by an external cron. The API also refreshes a stale benchmark in the background
when a seller opens a screen, which covers the common case -- this is for
bootstrapping a fresh box and for forcing a refresh after editing
app/adapters/_benchmarks.yml.

    docker exec mercai_intel_service python /app/scripts/refresh_benchmarks.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "intel"))

from shared.database import SessionLocal, engine  # noqa: E402

engine.echo = False
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format="  %(message)s")

from app.services import benchmarks  # noqa: E402


def main():
    db = SessionLocal()
    try:
        entries = benchmarks.config()
        if not entries:
            print("  no benchmarks configured in adapters/_benchmarks.yml")
            return 1
        print(f"Refreshing {len(entries)} configured benchmark(s)...\n")
        rows = benchmarks.refresh_all(db)
        for row in rows:
            if row.status == "ok":
                print(f"  ok   {row.source}:{row.external_category_id} "
                      f"({row.external_category_label})")
                print(f"       n={row.sample_size} of {row.catalogue_total}  "
                      f"p25={float(row.p25):,.0f}  median={float(row.median):,.0f}  "
                      f"p75={float(row.p75):,.0f}")
            else:
                print(f"  {row.status:<22} {row.source}:{row.external_category_id} "
                      f"(n={row.sample_size})")
        print()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
