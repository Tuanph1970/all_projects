"""Backlog #87 — pull deep history and the real index, for the EM-4 re-test.

    PYTHONPATH=. python3 tests/deep_history_dump.py [out.tsv] [index.tsv]

Not a test. It writes the two files the breadth studies read, and it exists
because every EM-4 number was power-limited in the same way:

* E&M's claim that *"all major stock market Bottoms have corresponded with
  extremely low MEI readings"* came back **n = 2** at the 60-session horizon.
  5.3 years of VN data contains **one** bear market; E&M spoke of 20 years.
  The claim was untestable for want of history, not refuted.
* The market was proxied by an **equal-weighted basket of the same 32 symbols
  the MEI was built from**, so proxy and measure were not independent — a test
  of internal consistency rather than of E&M's claim.
* 32 VN30 names is a thin reading of "the market" where Magee kept ~100
  charts, and the register flagged that before the work started.

What the vendor actually has, probed before writing this: VCI returns FPT from
**2009-03-27** (4,380 bars) and **VNINDEX from 2008-02-18** (4,641 bars). The
5-year limit was ours — `DEFAULT_YEARS_HISTORY`, inherited from the monolith —
and is now `settings.HISTORY_YEARS`.

Throttling
----------
vnstock 4.x applies a client-side quota (20 req/min for a guest), so the
service spaces calls ~3.1s apart and this script inherits that: ~92 symbols
costs about five minutes. Setting `VNSTOCK_API_KEY` raises it to 60/min
(Backlog #49).
"""
from __future__ import annotations

import sys
import time
import warnings
from typing import List

warnings.filterwarnings("ignore")

#: Magee kept ~100 charts. VN100 as the service defines it is 92 names, which
#: is the closest this market offers to his universe.
VN100: List[str] = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
    "AGG", "ANV", "ASM", "BWE", "CII", "CMG", "DBC", "DCM", "DGC", "DGW",
    "DIG", "DPM", "DXG", "ELC", "EVF", "FRT", "GEX", "HAG", "HCM", "HDC",
    "HDG", "HHV", "HSG", "HT1", "IDC", "KBC", "KDC", "KDH", "LPB", "MIG",
    "MSH", "NLG", "NT2", "NVL", "OCB", "PAN", "PC1", "PDR", "PHR", "PNJ",
    "PPC", "PTB", "PVD", "PVS", "PVT", "REE", "SBT", "SCS", "SIP", "SJS",
    "SZC", "TCH", "TLG", "TNH", "VCI", "VGC", "VHC", "VIX", "VND", "VOS",
    "VPI", "VTP",
]

START = "2008-01-01"
END = "2026-10-13"
SPACING_SECONDS = 3.2       # the guest quota, per Backlog #46/#49
MIN_BARS = 500              # below this a symbol is too short to contribute


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
    out_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/deep_bars.tsv"
    idx_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/deep_index.tsv"

    print(f"index -> {idx_path}", flush=True)
    with open(idx_path, "w") as fh:
        try:
            df = fetch("VNINDEX")
            n = write_rows(fh, "VNINDEX", df)
            print(f"   VNINDEX {n} bars, {str(df['time'].min())[:10]} -> "
                  f"{str(df['time'].max())[:10]}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"   VNINDEX FAILED: {type(exc).__name__} {exc}", flush=True)

    print(f"\nsymbols -> {out_path}", flush=True)
    kept = skipped = 0
    with open(out_path, "w") as fh:
        for i, sym in enumerate(VN100, 1):
            try:
                df = fetch(sym)
            except Exception as exc:  # noqa: BLE001
                print(f"   [{i:>2}/{len(VN100)}] {sym}: FAILED "
                      f"{type(exc).__name__}", flush=True)
                skipped += 1
                time.sleep(SPACING_SECONDS)
                continue
            if df is None or len(df) < MIN_BARS:
                print(f"   [{i:>2}/{len(VN100)}] {sym}: only "
                      f"{0 if df is None else len(df)} bars, skipped", flush=True)
                skipped += 1
            else:
                n = write_rows(fh, sym, df)
                kept += 1
                print(f"   [{i:>2}/{len(VN100)}] {sym}: {n} bars from "
                      f"{str(df['time'].min())[:10]}", flush=True)
            time.sleep(SPACING_SECONDS)

    print(f"\nkept {kept} symbols, skipped {skipped}", flush=True)


if __name__ == "__main__":
    main()
