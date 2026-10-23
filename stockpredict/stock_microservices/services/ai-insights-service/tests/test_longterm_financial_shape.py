"""The long-term recommender read the wrong orientation (dashboard N/A).

`get_longterm_recommendations` scores *consecutive years* of P/E improvement,
net-profit growth and ROE. It iterated the financial rows looking for keys
named `net_profit`, `pe`, `roe` **on each row**.

But vnstock serves financial statements as **one row per line item, with years
as columns**:

    {'item': 'Sales', 'item_en': 'Sales', 'item_id': 'sales',
     '2025': ..., '2024': ..., '2023': ..., '2022': ...}

So no row has a `net_profit` key — the *identity* is in `item_id` and the
*values* are under year keys. Nothing was ever found, nothing scored, and the
endpoint returned `{"recommendations": []}`, which the dashboard rendered as
N/A.

The real identifiers, read off the vendor rather than guessed:
`net_profit_loss_after_tax`, `pe_ratio`, `roe`.

A separate defect in `stock-data-service` compounded it — `period="annual"` is
not a vnstock period, so only one year of (quarterly) data arrived at all. See
`stock-data-service/tests/test_financial_period_vocabulary.py`.
"""
from __future__ import annotations

from app.services.insights_service import pivot_item_rows


ITEM_ROWS = [
    {"item": "Sales", "item_en": "Sales", "item_id": "sales",
     "2025": 70207688944553.0, "2024": 62962652134635.0, "2023": 52625174861333.0},
    {"item": "LNST", "item_en": "Net profit/(loss) after tax",
     "item_id": "net_profit_loss_after_tax",
     "2025": 9000.0, "2024": 8000.0, "2023": 7000.0},
]

RATIO_ROWS = [
    {"item": "P/E", "item_en": "P/E", "item_id": "pe_ratio",
     "2025": 18.0, "2024": 21.0, "2023": 25.0},
    {"item": "ROE", "item_en": "ROE (%)", "item_id": "roe",
     "2025": 28.5, "2024": 27.0, "2023": 26.0},
]


class TestPivot:

    def test_item_rows_become_one_row_per_year_newest_first(self):
        out = pivot_item_rows(ITEM_ROWS)
        assert [r["year"] for r in out] == [2025, 2024, 2023]

    def test_values_are_keyed_by_item_id(self):
        out = pivot_item_rows(ITEM_ROWS)
        assert out[0]["net_profit_loss_after_tax"] == 9000.0
        assert out[1]["sales"] == 62962652134635.0

    def test_the_ratio_identifiers_survive(self):
        out = pivot_item_rows(RATIO_ROWS)
        assert out[0]["pe_ratio"] == 18.0
        assert out[0]["roe"] == 28.5
        assert [r["pe_ratio"] for r in out] == [18.0, 21.0, 25.0]

    def test_a_frame_already_in_year_rows_is_passed_through(self):
        """Backward compatibility: if the vendor ever returns the old
        orientation, the pivot must not mangle it."""
        legacy = [{"year": 2025, "net_profit": 9000.0, "pe": 18.0}]
        assert pivot_item_rows(legacy) == legacy

    def test_rows_without_an_item_id_are_passed_through(self):
        other = [{"foo": 1}, {"bar": 2}]
        assert pivot_item_rows(other) == other

    def test_an_empty_input_is_inert(self):
        assert pivot_item_rows([]) == []
        assert pivot_item_rows(None) == []

    def test_non_numeric_and_missing_cells_do_not_raise(self):
        rows = [{"item_id": "pe_ratio", "2025": None, "2024": "n/a", "2023": 25.0}]
        out = pivot_item_rows(rows)
        years = [r["year"] for r in out]
        assert 2023 in years
        assert next(r for r in out if r["year"] == 2023)["pe_ratio"] == 25.0

    def test_duplicate_suffixed_year_columns_are_ignored(self):
        """`stock-data-service` de-duplicates a repeated vendor label to
        `2026__1`; those are not years and must not become rows."""
        rows = [{"item_id": "roe", "2025": 1.0, "2025__1": 2.0}]
        out = pivot_item_rows(rows)
        assert [r["year"] for r in out] == [2025]
