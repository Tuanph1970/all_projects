"""S-3 — persistence, the funnel-to-row mapping, and the API contract.

The point of this file is that a persisted scan must be a FAITHFUL and COMPLETE
record of what the scanner said on an evening. VT-5 compares that record against
what happened next, so a row that loses a rejection, or that can be recomputed
with hindsight, quietly makes the forward evaluation unfalsifiable.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Dict, List, Sequence

import pytest

from app.services.scanner.runner import (
    _rows,
    candidate_detail,
    config_payload,
    load_universe_bars,
)
from app.services.scanner.screen import KNOWN_PROVIDER_SEAMS, ScanConfig, run_scan
from app.services.signal.base import OHLCVBar
from tests.test_scanner_base import advance_then_base, bar

START = date(2022, 1, 3)


def ramp(n: int = 400, start: float = 20.0, step: float = 0.5) -> List[OHLCVBar]:
    return [bar(i, start + step * i, half_range=0.4, volume=1_000_000) for i in range(n)]


def thin(n: int = 400) -> List[OHLCVBar]:
    return [bar(i, 20.0 + 0.3 * i, half_range=0.4, volume=1) for i in range(n)]


def falling(n: int = 400) -> List[OHLCVBar]:
    return [bar(i, 200.0 - 0.3 * i, half_range=0.4, volume=1_000_000) for i in range(n)]


def _universe() -> Dict[str, List[OHLCVBar]]:
    return {
        "PLANT": advance_then_base(),   # candidate
        "RAMP": ramp(),                 # fails the base stage
        "DOWN": falling(),              # fails the trend template
        "THIN": thin(),                 # illiquid
        "SHORT": ramp(n=40),            # short history
        "NONE": [],                     # no bars
    }


# ---------------------------------------------------------------------------
# Every evaluated symbol becomes exactly one row
# ---------------------------------------------------------------------------

def test_every_bucket_becomes_a_row_with_the_right_verdict():
    u = _universe()
    r = run_scan(u, u["PLANT"][-1].date, ScanConfig())
    rows = _rows(r)
    by_symbol = {row["symbol"]: row["verdict"] for row in rows}
    assert by_symbol == {
        "PLANT": "CANDIDATE",
        "RAMP": "FAILED_BASE",
        "DOWN": "FAILED_TREND",
        "THIN": "ILLIQUID",
        "SHORT": "SHORT_HISTORY",
        "NONE": "NO_BARS",
    }


def test_the_row_count_matches_the_funnel_accounting():
    """If these two ever disagree, the stored run is not the scan that ran."""
    u = _universe()
    r = run_scan(u, u["PLANT"][-1].date, ScanConfig())
    assert len(_rows(r)) == r.accounting()["accounted"] == r.universe_total


def test_no_symbol_is_written_twice():
    u = _universe()
    r = run_scan(u, u["PLANT"][-1].date, ScanConfig())
    symbols = [row["symbol"] for row in _rows(r)]
    assert len(symbols) == len(set(symbols)), "a symbol with two verdicts has no verdict"


def test_a_seam_row_carries_its_remedy():
    seamed = list(ramp())
    for i in range(len(seamed) // 2, len(seamed)):
        seamed[i] = replace(seamed[i], close=seamed[i].close / 2.0,
                            high=seamed[i].high / 2.0, low=seamed[i].low / 2.0)
    r = run_scan({"SEAM": seamed}, seamed[-1].date, ScanConfig())
    row = _rows(r)[0]
    assert row["verdict"] == "PRICE_SEAM"
    assert "repair-history" in row["detail"]["remedy"], \
        "a seam exclusion is only actionable if it names the repair"


def test_names_cut_by_max_candidates_are_stored_as_qualified_not_as_failures():
    u = {f"P{i}": advance_then_base(start=20.0 + i) for i in range(4)}
    r = run_scan(u, u["P0"][-1].date, ScanConfig(max_candidates=2))
    verdicts = sorted(row["verdict"] for row in _rows(r))
    assert verdicts == ["CANDIDATE", "CANDIDATE",
                        "QUALIFIED_BEYOND_CUT", "QUALIFIED_BEYOND_CUT"]


# ---------------------------------------------------------------------------
# The stored detail is the evidence, not a summary
# ---------------------------------------------------------------------------

def test_a_rejected_symbol_stores_the_clause_that_rejected_it():
    """The whole reason rejections are persisted (FR-SCAN-API third endpoint)."""
    r = run_scan({"RAMP": ramp()}, ramp()[-1].date, ScanConfig())
    row = _rows(r)[0]
    assert row["verdict"] == "FAILED_BASE"
    assert row["detail"]["failed_clauses"], "a rejection with no named clause explains nothing"
    assert all("name" in c and "passed" in c and "detail" in c
               for c in row["detail"]["base"]["clauses"])


def test_candidate_detail_carries_the_population_behind_its_percentiles():
    u = {f"P{i}": advance_then_base(start=20.0 + i) for i in range(3)}
    r = run_scan(u, u["P0"][-1].date, ScanConfig())
    d = candidate_detail(r.candidates[0])
    assert d["momentum"]["ranked_universe"] == 3, \
        "a percentile without its population size is not a percentile"
    assert set(d["momentum"]["returns"]) == {"21", "63", "126"}
    assert d["base"]["window"]["length"] > 0
    assert d["base"]["squeeze"]["range_ratio"] is not None
    assert d["base"]["pivot"]["level"] >= d["trend"]["close"]


def test_trend_failures_store_the_averages_they_failed_against():
    r = run_scan({"DOWN": falling()}, falling()[-1].date, ScanConfig())
    detail = _rows(r)[0]["detail"]["trend"]
    assert detail["sma50"] is not None and detail["sma200"] is not None


# ---------------------------------------------------------------------------
# config_payload — a list is uninterpretable without its thresholds
# ---------------------------------------------------------------------------

def test_every_threshold_that_shapes_the_result_is_recorded():
    payload = config_payload(ScanConfig())
    for key in ("horizons", "min_avg_daily_value", "price_unit_vnd",
                "min_prior_advance_pct", "advance_lookback", "require_base",
                "base_max_drift_over_depth", "squeeze_max_ratio",
                "dryup_max_ratio", "ma_proximity_pct", "seam_allowlist"):
        assert key in payload, f"{key} shapes the candidate list but is not stored"


def test_the_payload_is_json_serialisable():
    import json
    json.dumps(config_payload(ScanConfig(seam_allowlist=frozenset({"VTP"}))))


def test_the_recorded_thresholds_track_an_override():
    payload = config_payload(ScanConfig(min_prior_advance_pct=5.0, require_base=False))
    assert payload["min_prior_advance_pct"] == 5.0 and payload["require_base"] is False


# ---------------------------------------------------------------------------
# The seam allowlist has ONE definition
# ---------------------------------------------------------------------------

def test_the_cli_and_the_library_share_one_seam_allowlist():
    """Three copies of this list is how the API, the nightly job and the CLI
    stop agreeing about which seams are real."""
    from tests.s1_momentum_scan import SEAM_ALLOWLIST
    assert SEAM_ALLOWLIST is KNOWN_PROVIDER_SEAMS


def test_the_api_shares_it_too():
    from app.api.routes import SCANNER_SEAM_ALLOWLIST
    assert SCANNER_SEAM_ALLOWLIST is KNOWN_PROVIDER_SEAMS


# ---------------------------------------------------------------------------
# load_universe_bars — a fetch outage must not look like a small universe
# ---------------------------------------------------------------------------

class _FakeClient:
    def __init__(self, data: Dict[str, List[dict]], fail: Sequence[str] = ()):
        self.data = data
        self.fail = set(fail)
        self.calls: List[str] = []

    async def fetch_ohlcv(self, symbol, days=300, end_date=None):
        self.calls.append(symbol)
        if symbol in self.fail:
            raise RuntimeError("upstream down")
        return self.data.get(symbol, [])


def _raw(n: int = 5) -> List[dict]:
    return [
        {"date": str(START + timedelta(days=i)), "open": 10.0, "high": 11.0,
         "low": 9.0, "close": 10.5, "volume": 1000}
        for i in range(n)
    ]


async def test_a_failed_fetch_yields_an_empty_series_not_a_missing_key():
    client = _FakeClient({"A": _raw(), "B": _raw()}, fail=["B"])
    bars = await load_universe_bars(client, ["A", "B"], date(2022, 2, 1))
    assert set(bars) == {"A", "B"}, \
        "dropping the symbol would make an outage look like a small universe"
    assert len(bars["A"]) == 5 and bars["B"] == []


async def test_unparseable_rows_are_skipped_not_fatal():
    client = _FakeClient({"A": _raw(2) + [{"date": "nonsense"}, {}]})
    bars = await load_universe_bars(client, ["A"], date(2022, 2, 1))
    assert len(bars["A"]) == 2


async def test_every_requested_symbol_is_fetched_exactly_once():
    client = _FakeClient({s: _raw() for s in ("A", "B", "C")})
    await load_universe_bars(client, ["A", "B", "C"], date(2022, 2, 1), concurrency=2)
    assert sorted(client.calls) == ["A", "B", "C"]
