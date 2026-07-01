"""T9 — HttpPriceSource adapter (network mocked, offline)."""
from __future__ import annotations

import httpx
import pandas as pd
import pytest

from event_reaction.exceptions import InsufficientDataError
from event_reaction.ingest import HttpPriceSource


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestHistory:
    def test_returns_tz_aware_sorted_series(self):
        payload = {
            "data": [
                {"date": "2022-01-05", "close": 102.0},
                {"date": "2022-01-03", "close": 100.0},  # out of order on purpose
                {"date": "2022-01-04", "close": 101.0},
            ]
        }

        def handler(request):
            assert request.url.path.endswith("/stocks/AAA/history")
            return httpx.Response(200, json=payload)

        src = HttpPriceSource("http://gw", client=_client(handler))
        s = src.history("AAA")
        assert str(s.index.tz) == "UTC"
        assert s.index.is_monotonic_increasing
        assert list(s.to_numpy()) == [100.0, 101.0, 102.0]

    def test_non_200_raises(self):
        src = HttpPriceSource("http://gw", client=_client(lambda r: httpx.Response(503)))
        with pytest.raises(InsufficientDataError):
            src.history("AAA")

    def test_empty_payload_raises(self):
        src = HttpPriceSource(
            "http://gw", client=_client(lambda r: httpx.Response(200, json={"data": []}))
        )
        with pytest.raises(InsufficientDataError):
            src.history("AAA")

    def test_passes_date_params(self):
        seen = {}

        def handler(request):
            seen["params"] = dict(request.url.params)
            return httpx.Response(200, json={"data": [{"date": "2022-01-03", "close": 1.0}]})

        src = HttpPriceSource("http://gw", client=_client(handler))
        src.history("AAA", start=pd.Timestamp("2022-01-01", tz="UTC"),
                    end=pd.Timestamp("2022-02-01", tz="UTC"))
        assert seen["params"]["start_date"] == "2022-01-01"
        assert seen["params"]["end_date"] == "2022-02-01"
