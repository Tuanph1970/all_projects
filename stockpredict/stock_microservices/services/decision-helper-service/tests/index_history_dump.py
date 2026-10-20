"""EM-6 — pull the VN index series the multi-index confirmation gate needs.

    PYTHONPATH=. python3 tests/index_history_dump.py [out.tsv]

Not a test. Companion to `deep_history_dump.py` (Backlog #87), which pulled
VNINDEX only.

Why a separate dump
-------------------
EM-6 asks whether a trend signal should be gated on agreement between several
market indices, which is E&M's most durable tenet (Ch 3 tenet 8: *"no valid
trend-change signal from one average alone"*) in Bassetti's 9th-edition form —
read the broad trend from three indices together, and treat disagreement
among them as itself a hedge signal.

That needs more than one index, and the register flagged a risk before any
work started: **VNINDEX and VN30 share most of their weight, so they may
confirm trivially.** This script supplies the data that settles it.

What the vendor has, probed before writing this (VCI, start=2000-01-01):

    VNINDEX      5,672 bars   2004-01-05 ->
    VN30         3,669 bars   2012-02-06 ->
    HNXINDEX     5,217 bars   2005-07-14 ->
    HNX30        3,522 bars   2012-07-09 ->
    UPCOMINDEX   4,238 bars   2009-06-25 ->
    VN100        1,082 bars   2022-06-20 ->     (too short to be a witness)

Two notes that matter to the reader:

* **VNINDEX reaches 2004, not 2008.** `deep_history_dump.py` set
  `START = "2008-01-01"`, so #87's dump misses 2004-2008 — which contains the
  entire 2006-07 VN bubble *and its top* (VNINDEX ~1170 in March 2007). That
  is a gap in the EM-4 re-test, not in this one, and is logged as its own
  backlog item rather than fixed here.
* **The witnesses start at different dates.** Any agreement statistic must be
  computed on each pair's *common* history and report its own window, or a
  pair that simply has less overlap will look more agreeable.
"""
from __future__ import annotations

import sys
import time
import warnings
from typing import List

warnings.filterwarnings("ignore")

#: Every index VCI serves with enough history to act as a witness. VN100 is
#: excluded deliberately: 1,082 bars from 2022 cannot speak to a primary trend.
INDICES: List[str] = ["VNINDEX", "VN30", "HNXINDEX", "HNX30", "UPCOMINDEX"]

START = "2000-01-01"        # earlier than any series; the vendor clamps it
END = "2026-10-20"
SPACING_SECONDS = 3.2       # the vnstock guest quota, per Backlog #46/#49


def fetch(symbol: str):
    from vnstock import Quote

    return Quote(symbol=symbol, source="VCI").history(
        start=START, end=END, interval="1D"
    )


def write_rows(handle, symbol: str, df) -> int:
    written = 0
    for row in df.itertuples(index=False):
        day = str(row.time)[:10]
        try:
            handle.write(
                f"{symbol}\t{day}\t{float(row.open)}\t{float(row.high)}\t"
                f"{float(row.low)}\t{float(row.close)}\t{float(row.volume)}\n"
            )
            written += 1
        except (AttributeError, TypeError, ValueError):
            continue
    return written


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/vn_indices.tsv"
    print(f"indices -> {out_path}", flush=True)

    kept = 0
    with open(out_path, "w") as fh:
        for i, code in enumerate(INDICES, 1):
            try:
                df = fetch(code)
            except Exception as exc:  # noqa: BLE001
                print(f"   [{i}/{len(INDICES)}] {code}: FAILED "
                      f"{type(exc).__name__} {exc}", flush=True)
                time.sleep(SPACING_SECONDS)
                continue
            if df is None or df.empty:
                print(f"   [{i}/{len(INDICES)}] {code}: EMPTY", flush=True)
            else:
                n = write_rows(fh, code, df)
                kept += 1
                print(f"   [{i}/{len(INDICES)}] {code}: {n} bars, "
                      f"{str(df['time'].min())[:10]} -> "
                      f"{str(df['time'].max())[:10]}", flush=True)
            time.sleep(SPACING_SECONDS)

    print(f"\nkept {kept} of {len(INDICES)} indices", flush=True)


if __name__ == "__main__":
    main()
