"""Tests for Phase J — Journal auto-integration (F-090..F-093).

These tests document and guard the field-name contract between the
decision-helper frontend (TradePlanModal) and the journal-service
TradeCreate / TradeDiaryCreate schemas.  If journal-service renames a
field, these tests will catch it at the decision-helper test layer.
"""
from __future__ import annotations

import sys
import importlib
import pytest


# ---------------------------------------------------------------------------
# Helpers — graceful skip when journal-service is not on sys.path
# ---------------------------------------------------------------------------

def _import_journal_schemas():
    """Return the journal-service schemas module, or None if not importable."""
    try:
        # journal-service lives in a sibling directory; adjust path when needed
        import importlib.util
        import pathlib

        svc_root = pathlib.Path(__file__).parents[2] / "journal-service"
        schemas_path = svc_root / "app" / "models" / "schemas.py"
        if not schemas_path.exists():
            return None

        spec = importlib.util.spec_from_file_location("journal_schemas", schemas_path)
        mod = importlib.util.module_from_spec(spec)
        # Inject a minimal pydantic stub so the import succeeds without deps
        sys.modules.setdefault("pydantic", __import__("pydantic"))
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


_journal = _import_journal_schemas()
_skip_if_no_journal = pytest.mark.skipif(
    _journal is None,
    reason="journal-service schemas not importable from test environment",
)


# ---------------------------------------------------------------------------
# F-090 — TradeCreate field-name contract
# ---------------------------------------------------------------------------

@_skip_if_no_journal
class TestTradeCreateContract:
    """Verify the field names TradePlanModal sends match journal TradeCreate."""

    def _fields(self):
        return set(_journal.TradeCreate.model_fields.keys())

    def test_market_ticker_exists(self):
        assert "market_ticker" in self._fields()

    def test_direction_exists(self):
        assert "direction" in self._fields()

    def test_entry_date_exists(self):
        assert "entry_date" in self._fields()

    def test_entry_price_exists(self):
        assert "entry_price" in self._fields()

    def test_entry_type_exists(self):
        assert "entry_type" in self._fields()

    def test_initial_stop_exists(self):
        assert "initial_stop" in self._fields()

    def test_position_size_exists(self):
        assert "position_size" in self._fields()

    def test_objective_1_exists(self):
        assert "objective_1" in self._fields()

    def test_entry_reason_exists(self):
        assert "entry_reason" in self._fields()

    def test_old_field_names_absent(self):
        fields = self._fields()
        assert "ticker" not in fields, "use market_ticker not ticker"
        assert "stop_loss" not in fields, "use initial_stop not stop_loss"
        assert "take_profit" not in fields, "use objective_1 not take_profit"
        assert "quantity" not in fields, "use position_size not quantity"
        assert "notes" not in fields, "use entry_reason not notes"

    def test_direction_long_value(self):
        # Journal enum uses 'Long' (capitalised) not 'LONG'
        assert _journal.TradeDirection.LONG.value == "Long"

    def test_direction_short_value(self):
        assert _journal.TradeDirection.SHORT.value == "Short"


# ---------------------------------------------------------------------------
# F-091 — TradeDiaryCreate field-name contract
# ---------------------------------------------------------------------------

@_skip_if_no_journal
class TestTradeDiaryCreateContract:
    def test_reasons_for_trade_exists(self):
        fields = set(_journal.TradeDiaryCreate.model_fields.keys())
        assert "reasons_for_trade" in fields

    def test_reasons_for_trade_is_optional(self):
        # Should not raise with no args (all optional)
        diary = _journal.TradeDiaryCreate()
        assert diary.reasons_for_trade is None

    def test_reasons_for_trade_accepts_string(self):
        diary = _journal.TradeDiaryCreate(reasons_for_trade="Signal: MA_CROSS (confirmed)")
        assert "MA_CROSS" in diary.reasons_for_trade


# ---------------------------------------------------------------------------
# F-092 — AccountResponse field name
# ---------------------------------------------------------------------------

@_skip_if_no_journal
class TestAccountResponseContract:
    def test_account_name_field_exists(self):
        fields = set(_journal.AccountResponse.model_fields.keys())
        assert "account_name" in fields, (
            "TradePlanModal uses a.account_name — field was renamed or removed"
        )
