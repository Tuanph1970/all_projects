"""PriceHistorySource — daily closes from stock-data-service, via MockTransport.

No real network: the transport is injected, mirroring how the other ingest adapters in
this service are tested.
"""
from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.ingest.price_history import (
    PriceHistorySource,
    PriceSeries,
    PriceUnavailableError,
)

START, END = date(2026, 9, 1), date(2026, 9, 30)


def source(handler) -> PriceHistorySource:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return PriceHistorySource("http://stock-data-service:8001", client=client)


def payload(rows):
    return lambda request: httpx.Response(200, json={"symbol": "NTP", "data": rows})


def test_history_returns_ascending_closes():
    s = source(payload([
        {"date": "2026-09-03", "close": 30.0},
        {"date": "2026-09-01", "close": 10.0},
        {"date": "2026-09-02", "close": 20.0},
    ])).history("ntp", START, END)
    assert s.symbol == "NTP"
    assert s.dates == (date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3))
    assert s.closes == (10.0, 20.0, 30.0)


def test_the_request_carries_the_window():
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"data": [{"date": "2026-09-01", "close": 10.0}]})

    source(handler).history("NTP", START, END)
    assert seen == {"start_date": "2026-09-01", "end_date": "2026-09-30"}


def test_adjusted_close_is_preferred_when_present():
    """A stock dividend inside the window shows as a fake loss on raw closes, so
    adj_close wins wherever the ingest has populated it."""
    s = source(payload([
        {"date": "2026-09-01", "close": 100.0, "adj_close": 87.0},
        {"date": "2026-09-02", "close": 101.0, "adj_close": 88.0},
    ])).history("TPB", START, END)
    assert s.closes == (87.0, 88.0)
    assert s.adjusted is True


def test_falls_back_to_raw_close_and_says_so():
    """What actually happens in this database today: nothing writes adj_close, so the
    flag must come back False rather than the caller assuming adjusted prices."""
    s = source(payload([
        {"date": "2026-09-01", "close": 100.0, "adj_close": None},
        {"date": "2026-09-02", "close": 101.0},
    ])).history("NTP", START, END)
    assert s.closes == (100.0, 101.0)
    assert s.adjusted is False


def test_one_missing_adj_close_marks_the_whole_series_unadjusted():
    s = source(payload([
        {"date": "2026-09-01", "close": 100.0, "adj_close": 100.0},
        {"date": "2026-09-02", "close": 101.0},
    ])).history("NTP", START, END)
    assert s.adjusted is False


def test_duplicate_dates_keep_the_last_row():
    s = source(payload([
        {"date": "2026-09-01", "close": 10.0},
        {"date": "2026-09-01", "close": 11.0},
    ])).history("NTP", START, END)
    assert s.closes == (11.0,)


def test_datetime_stamps_are_accepted():
    s = source(payload([{"date": "2026-09-01T00:00:00Z", "close": 10.0}])).history(
        "NTP", START, END)
    assert s.dates == (date(2026, 9, 1),)


def test_unparseable_and_priceless_rows_are_skipped():
    s = source(payload([
        {"date": "not-a-date", "close": 1.0},
        {"date": "2026-09-02", "close": None},
        {"date": "2026-09-03", "close": 30.0},
    ])).history("NTP", START, END)
    assert s.dates == (date(2026, 9, 3),)


@pytest.mark.parametrize("handler,match", [
    (lambda r: httpx.Response(404, json={"detail": "nope"}), "404"),
    (lambda r: httpx.Response(200, json={"data": []}), "no price history"),
    (lambda r: httpx.Response(200, json={"data": [{"date": "2026-09-01"}]}), "no usable closes"),
])
def test_unavailable_history_raises(handler, match):
    with pytest.raises(PriceUnavailableError, match=match):
        source(handler).history("NTP", START, END)


def test_a_transport_failure_is_wrapped_not_leaked():
    def boom(request):
        raise httpx.ConnectError("refused")
    with pytest.raises(PriceUnavailableError, match="unreachable"):
        source(boom).history("NTP", START, END)


# ---------------------------------------------------------------------------
# index_at_or_before — the reference-bar lookup the scorer depends on
# ---------------------------------------------------------------------------

SERIES = PriceSeries(
    symbol="NTP",
    dates=(date(2026, 9, 1), date(2026, 9, 3), date(2026, 9, 7)),
    closes=(10.0, 20.0, 30.0),
    adjusted=False,
)


@pytest.mark.parametrize("when,expected", [
    (date(2026, 8, 31), None),     # before the series starts
    (date(2026, 9, 1), 0),         # exact hit
    (date(2026, 9, 2), 0),         # no bar that day -> the last one known
    (date(2026, 9, 3), 1),
    (date(2026, 9, 6), 1),
    (date(2026, 9, 7), 2),
    (date(2026, 9, 30), 2),        # after the end -> the last bar
])
def test_index_at_or_before(when, expected):
    assert SERIES.index_at_or_before(when) == expected
