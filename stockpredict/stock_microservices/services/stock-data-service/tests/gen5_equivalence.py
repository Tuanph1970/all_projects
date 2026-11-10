"""Backlog #142 — does the gen-5 call style return what gen-4 returned?

    PYTHONPATH=. python3 tests/gen5_equivalence.py [SYMBOL]

Not a unit test: it hits the live vendor, so it lives here as a CLI alongside
`deep_history_dump.py` and `s1_momentum_scan.py` rather than in the suite.

WHY THIS EXISTS BEFORE THE MIGRATION, NOT AFTER. The vendor's advice is to move
gen-4 `Vnstock().stock(...)` call style to the gen-5 direct classes, which gen 6
keeps. The two are NOT a mechanical rename: `StockComponents._initialize_components`
decides which source each component gets, and for listing it hardcodes
`Listing(source="KBS")` EVEN WHEN the components' source is VCI. Measured
2026-11-10: `Listing("KBS").all_symbols()` returns 1,517 rows and
`Listing("VCI").all_symbols()` returns 1,757. So a naive migration to
`Listing(source=settings.VNSTOCK_DATA_SOURCE)` would silently change the
universe every downstream consumer reads — the scanner's included.

This script pins the mapping down endpoint by endpoint so the migration can be
checked rather than believed, and so the #142 adapter has a statement of what
"the same data" means for each of the 16 endpoints we depend on.
"""
from __future__ import annotations

import hashlib
import io
import os
import contextlib
import sys
import time
import warnings
from datetime import date, timedelta
from typing import Any, Callable, Optional, Tuple

warnings.filterwarnings("ignore")

#: Seconds between live calls, overridable with GEN5_SPACING. The guard in
#: stock_service is not in play here and the vendor throttles hard: at 2.0s the
#: GEN-4 side started read-timing-out partway through a full sweep (#144 measured
#: the same cliff on construction). 6s completes it. If a run shows ERROR rows
#: with "gen5=ok", raise this before concluding anything about the call styles.
SPACING = float(os.environ.get("GEN5_SPACING", "6.0"))


def _quiet(fn: Callable[[], Any]) -> Any:
    """Run `fn` with the vendor's banner swallowed."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn()


def fingerprint(obj: Any) -> str:
    """Shape and content of a result, stable enough to compare two calls.

    Columns and row count, plus a hash of the values. Index is ignored: the two
    call styles build the frame through different paths and an index difference
    is not a data difference.
    """
    try:
        import pandas as pd
        if isinstance(obj, pd.Series):
            obj = obj.to_frame().T
        if isinstance(obj, pd.DataFrame):
            cols = list(map(str, obj.columns))
            body = obj.reset_index(drop=True).to_csv(index=False).encode()
            return (f"rows={len(obj)} cols={len(cols)} "
                    f"colhash={hashlib.sha256(','.join(cols).encode()).hexdigest()[:8]} "
                    f"datahash={hashlib.sha256(body).hexdigest()[:12]}")
    except ImportError:
        pass
    if obj is None:
        return "None"
    if hasattr(obj, "__len__"):
        return f"len={len(obj)}"
    return f"obj={type(obj).__name__}"


def main(argv: list[str]) -> int:
    """`argv[1]` is the symbol; `argv[2:]` optionally filters to endpoints whose
    label contains any of those substrings — a full sweep is ~2 minutes of live
    calls, and re-checking one row should not cost that."""
    symbol = (argv[1] if len(argv) > 1 else "FPT").upper()
    only = [a.lower() for a in argv[2:]]
    source = "VCI"
    end = date.today()
    start = end - timedelta(days=20)

    from vnstock import Company, Finance, Listing, Quote, Trading, Vnstock

    print(f"gen-4 vs gen-5 equivalence — {symbol} @ {source}, {start}..{end}")
    print(f"  spacing {SPACING}s between live calls\n")

    g4 = _quiet(lambda: Vnstock(source=source).stock(symbol=symbol, source=source))

    # (label, gen-4 callable, gen-5 callable)
    #
    # The gen-5 column is written to MATCH gen-4, not to look tidy. `Listing`
    # takes source="KBS" because that is what StockComponents hands us; using
    # the configured source here would be a different query (see the docstring).
    cases: list[Tuple[str, Callable[[], Any], Callable[[], Any]]] = [
        ("quote.history",
         lambda: g4.quote.history(start=str(start), end=str(end), interval="1D"),
         lambda: Quote(symbol=symbol, source=source).history(
             start=str(start), end=str(end), interval="1D")),
        ("company.overview",
         lambda: g4.company.overview(),
         lambda: Company(symbol=symbol, source=source).overview()),
        ("company.shareholders",
         lambda: g4.company.shareholders(),
         lambda: Company(symbol=symbol, source=source).shareholders()),
        ("company.news",
         lambda: g4.company.news(),
         lambda: Company(symbol=symbol, source=source).news()),
        ("company.events",
         lambda: g4.company.events(),
         lambda: Company(symbol=symbol, source=source).events()),
        ("company.trading_stats",
         lambda: g4.company.trading_stats(),
         lambda: Company(symbol=symbol, source=source).trading_stats()),
        ("finance.ratio",
         lambda: g4.finance.ratio(period="year", lang="en"),
         lambda: Finance(symbol=symbol, source=source).ratio(period="year", lang="en")),
        ("finance.income_statement",
         lambda: g4.finance.income_statement(period="year", lang="en"),
         lambda: Finance(symbol=symbol, source=source).income_statement(
             period="year", lang="en")),
        ("finance.balance_sheet",
         lambda: g4.finance.balance_sheet(period="year", lang="en"),
         lambda: Finance(symbol=symbol, source=source).balance_sheet(
             period="year", lang="en")),
        ("finance.cash_flow",
         lambda: g4.finance.cash_flow(period="year", lang="en"),
         lambda: Finance(symbol=symbol, source=source).cash_flow(
             period="year", lang="en")),
        ("listing.all_symbols",
         lambda: g4.listing.all_symbols(),
         lambda: Listing(source="KBS").all_symbols()),
        ("listing.industries_icb",
         lambda: g4.listing.industries_icb(),
         lambda: Listing(source="KBS").industries_icb()),
        ("listing.symbols_by_industries",
         lambda: g4.listing.symbols_by_industries(),
         lambda: Listing(source="KBS").symbols_by_industries()),
        ("listing.symbols_by_group",
         lambda: g4.listing.symbols_by_group("VN30"),
         lambda: Listing(source="KBS").symbols_by_group("VN30")),
        ("trading.price_board",
         lambda: g4.trading.price_board([symbol, "VNM"]),
         lambda: Trading(symbol=symbol, source=source).price_board([symbol, "VNM"])),
    ]

    if only:
        cases = [c for c in cases if any(o in c[0].lower() for o in only)]
        print(f"  filtered to {len(cases)} endpoint(s): "
              f"{', '.join(c[0] for c in cases)}\n")

    same = differ = failed = 0
    rows: list[str] = []
    for label, f4, f5 in cases:
        def run(fn) -> Tuple[Optional[str], Optional[str]]:
            try:
                return fingerprint(_quiet(fn)), None
            except Exception as exc:                       # noqa: BLE001
                return None, f"{type(exc).__name__}: {str(exc)[:60]}"

        fp4, err4 = run(f4)
        time.sleep(SPACING)
        fp5, err5 = run(f5)
        time.sleep(SPACING)

        if err4 or err5:
            failed += 1
            verdict = "ERROR"
            detail = f"gen4={err4 or 'ok'} | gen5={err5 or 'ok'}"
        elif fp4 == fp5:
            same += 1
            verdict = "SAME"
            detail = fp4
        else:
            differ += 1
            verdict = "DIFFERS"
            detail = f"\n      gen4: {fp4}\n      gen5: {fp5}"
        rows.append(f"  {verdict:<8} {label:<30} {detail}")
        print(rows[-1], flush=True)

    print(f"\n  same={same} differs={differ} error={failed} of {len(cases)}")
    print("\n  A DIFFERS row is not automatically a defect — intraday endpoints")
    print("  (price_board, news, trading_stats) move between two calls seconds")
    print("  apart. Read the fingerprints: a column-hash change is a real shape")
    print("  difference, a datahash-only change on a live endpoint is not.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
