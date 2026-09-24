"""Parser tests for the TCBS daily mail (FR-BM-EXTRACT).

Fixtures are the three real emails the operator supplied (tests/fixtures/tcb_mail_*.txt):
  1 — Vietnamese, has section 1 (Báo cáo phân tích mới), 4 corporate items, NTP "Chờ mua"
  2 — English, no section 1, 2 corporate items, MSN "Hold"
  3 — Vietnamese, no section 1, 2 corporate items, OIL "Chờ mua"

Between them they cover both languages, both number formats, both heading sets, a
present and an absent section 1, and a mail (3) that omits the foreign buy/sell split.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.ingest.tcb_mail_parser import (
    ACTION_BUY,
    ACTION_HOLD,
    ACTION_SELL,
    ACTION_WATCH,
    detect_lang,
    normalize_action,
    parse_tcb_mail,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(n: int) -> str:
    return (FIXTURES / f"tcb_mail_{n}.txt").read_text(encoding="utf-8")


# Each mail is pasted the day of / after the session it describes.
_REFERENCE = {1: date(2026, 9, 22), 2: date(2026, 9, 22), 3: date(2026, 9, 23)}


@pytest.fixture(params=[1, 2, 3])
def mail_no(request):
    return request.param


@pytest.fixture
def parsed(mail_no):
    return parse_tcb_mail(_load(mail_no), reference_date=_REFERENCE[mail_no])


# ---------------------------------------------------------------------------
# Language + number formats (EC-B5: vi 1.799,67 vs en 1,816.93)
# ---------------------------------------------------------------------------

def test_language_detected():
    assert detect_lang(_load(1)) == "vi"
    assert detect_lang(_load(2)) == "en"
    assert detect_lang(_load(3)) == "vi"


@pytest.mark.parametrize("n,close,pct,pts", [
    (1, 1799.67, -0.88, -15.99),   # "Đánh mất 0,88% (−15,99 điểm) ... 1.799,67"
    (2, 1816.93, 0.96, 17.26),     # "0.96% rebound (+17.26 points) ... 1,816.93"
    (3, 1801.65, -0.84, -15.28),
])
def test_vnindex_numbers(n, close, pct, pts):
    p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
    assert p.vnindex_close == pytest.approx(close)
    assert p.vnindex_change_pct == pytest.approx(pct)
    assert p.vnindex_change_pts == pytest.approx(pts)


def test_percent_sign_taken_from_points():
    """The percent is printed unsigned ("Đánh mất 0,88%"); the sign must come from the
    bracketed points figure, or a down day reads as an up day."""
    p1 = parse_tcb_mail(_load(1), reference_date=_REFERENCE[1])
    p2 = parse_tcb_mail(_load(2), reference_date=_REFERENCE[2])
    assert p1.vnindex_change_pct < 0 and p1.vnindex_change_pts < 0
    assert p2.vnindex_change_pct > 0 and p2.vnindex_change_pts > 0


@pytest.mark.parametrize("n,matched,volume,putthrough,total", [
    (1, 13665.8, 511.3, 3651.6, 17317.4),
    (2, 10237.9, 391.8, 2750.2, 12988.2),
    (3, 12617.0, 481.2, 5128.6, 17745.6),
])
def test_liquidity(n, matched, volume, putthrough, total):
    p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
    assert p.matched_value_bn == pytest.approx(matched)
    assert p.matched_volume_m == pytest.approx(volume)
    assert p.putthrough_bn == pytest.approx(putthrough)
    assert p.total_value_bn == pytest.approx(total)


def test_liquidity_arithmetic_holds(parsed):
    """matched + put-through == total, within the rounding TCBS prints (EC-B6)."""
    assert parsed.matched_value_bn + parsed.putthrough_bn == pytest.approx(
        parsed.total_value_bn, abs=0.5)


# ---------------------------------------------------------------------------
# Foreign flow — sign convention: net sell is negative
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,net,buy,sell,ytd", [
    (1, -664.2, 2442.3, 3106.5, -94117.0),
    (2, 54.1, 1597.8, 1543.7, -94064.0),
    (3, -1062.0, None, None, -95126.0),   # mail 3 omits the buy/sell split
])
def test_foreign_flow(n, net, buy, sell, ytd):
    p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
    assert p.foreign_net_bn == pytest.approx(net)
    assert (p.foreign_buy_bn is None) if buy is None else p.foreign_buy_bn == pytest.approx(buy)
    assert (p.foreign_sell_bn is None) if sell is None else p.foreign_sell_bn == pytest.approx(sell)
    assert p.foreign_ytd_net_bn == pytest.approx(ytd)


def test_net_sell_is_negative_net_buy_is_positive():
    assert parse_tcb_mail(_load(1), reference_date=_REFERENCE[1]).foreign_net_bn < 0  # bán ròng
    assert parse_tcb_mail(_load(2), reference_date=_REFERENCE[2]).foreign_net_bn > 0  # net purchase


@pytest.mark.parametrize("n,top_sell,top_buy", [
    (1, "VHM, VIC, FPT, SSI, SHB", "MCH, VPB, CTG, BSR, MBB"),
    (2, "TCB, VHM, VPB, BVH, VCB", "SBT, MCH, VIC, VNM, MSN"),
    (3, "VPB, ACB, VHM, TCB, FRT", "VIC, TPB, DCM, VPI, DPM"),
])
def test_foreign_top_tickers(n, top_sell, top_buy):
    p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
    assert p.foreign_top_sell == top_sell
    assert p.foreign_top_buy == top_buy


# ---------------------------------------------------------------------------
# Technicals
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,ma5,ma10,ma20,ma50", [
    (1, 1812.0, 1813.0, 1810.0, 1776.0),
    (2, 1813.0, 1812.0, 1814.0, 1775.0),
    (3, 1811.0, 1809.0, 1816.0, 1775.0),
])
def test_moving_averages(n, ma5, ma10, ma20, ma50):
    p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
    assert (p.ma5, p.ma10, p.ma20, p.ma50) == (ma5, ma10, ma20, ma50)


def test_support_and_resistance_sentences_captured(parsed):
    assert parsed.support_txt and parsed.resistance_txt


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def test_section1_present_only_in_mail_1():
    assert "HVN" in parse_tcb_mail(_load(1), reference_date=_REFERENCE[1]).reports_txt
    assert parse_tcb_mail(_load(2), reference_date=_REFERENCE[2]).reports_txt is None
    assert parse_tcb_mail(_load(3), reference_date=_REFERENCE[3]).reports_txt is None


def test_macro_paragraphs(parsed):
    assert parsed.macro_domestic_txt and parsed.macro_intl_txt
    # "Trong nước:"/"Domestic:" must not swallow the international paragraph.
    assert "Quốc tế" not in parsed.macro_domestic_txt
    assert "International:" not in parsed.macro_domestic_txt


@pytest.mark.parametrize("n,symbols", [
    (1, ["MSN", "SSB", "MWG", "TLG"]),
    (2, ["DPG", "PNJ"]),
    (3, ["TPB", "HDB"]),
])
def test_corporate_items(n, symbols):
    p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
    assert [c.symbol for c in p.companies] == symbols
    assert all(len(c.item_text) > 50 for c in p.companies)


def test_corporate_item_text_is_not_truncated_at_the_next_ticker():
    p = parse_tcb_mail(_load(1), reference_date=_REFERENCE[1])
    msn = next(c for c in p.companies if c.symbol == "MSN")
    assert "WinCommerce" in msn.item_text          # runs to the end of its paragraph
    assert "Lê Tuấn Anh" not in msn.item_text      # but stops before SSB's item


# ---------------------------------------------------------------------------
# Recommendations — section 3 (the watchlist feed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,symbol,action,label", [
    (1, "NTP", ACTION_WATCH, "Chờ mua"),
    (2, "MSN", ACTION_HOLD, "Hold"),
    (3, "OIL", ACTION_WATCH, "Chờ mua"),
])
def test_recommendation_extracted(n, symbol, action, label):
    p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
    assert len(p.recos) == 1
    reco = p.recos[0]
    assert reco.symbol == symbol
    assert reco.action == action
    assert reco.label_verbatim == label


def test_every_sample_yields_a_watchlist_candidate():
    """All three mails must produce an actionable row — the reason WATCH exists."""
    for n in (1, 2, 3):
        p = parse_tcb_mail(_load(n), reference_date=_REFERENCE[n])
        assert p.recos and p.recos[0].action is not None


def test_rationale_survives_hyphens_in_the_body():
    """NTP's rationale opens "Giá PVC tuần 14-18/9" — the hyphen there must not be read
    as the label separator, or the label becomes "Chờ mua - Giá PVC tuần 14"."""
    p = parse_tcb_mail(_load(1), reference_date=_REFERENCE[1])
    reco = p.recos[0]
    assert reco.label_verbatim == "Chờ mua"
    assert reco.rationale.startswith("Giá PVC tuần 14-18/9")
    assert reco.rationale.endswith("NĐT nên theo dõi thêm đối với cổ phiếu này.")


@pytest.mark.parametrize("label,expected", [
    ("Chờ mua", ACTION_WATCH),
    ("Cho mua", ACTION_WATCH),          # accent-stripped input
    ("Wait to buy", ACTION_WATCH),
    ("Theo dõi", ACTION_WATCH),
    ("Mua", ACTION_BUY),
    ("MUA NGAY", ACTION_BUY),
    ("Buy Now", ACTION_BUY),
    ("Khả quan", ACTION_BUY),
    ("Kém khả quan", ACTION_SELL),      # must not degrade to "khả quan" -> BUY
    ("Bán", ACTION_SELL),
    ("Sell", ACTION_SELL),
    ("Nắm giữ", ACTION_HOLD),
    ("Hold", ACTION_HOLD),
    ("Trung lập", ACTION_HOLD),
    ("Xin chào", None),
    ("", None),
])
def test_normalize_action(label, expected):
    assert normalize_action(label) == expected


def test_longest_label_wins_over_its_substring():
    """"Chờ mua" contains "mua"; the map must not collapse a wait-to-buy into a buy."""
    assert normalize_action("Chờ mua") == ACTION_WATCH
    assert normalize_action("Chờ mua") != ACTION_BUY


# ---------------------------------------------------------------------------
# Session date hint
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,expected", [
    (1, date(2026, 9, 21)),   # despite SSB's 23/9-22/10 window and MWG's 7/10 ex-date
    (2, date(2026, 9, 22)),   # "the afternoon of 22 September"
    (3, date(2026, 9, 23)),   # "chiều 23/9 theo giờ Việt Nam"
])
def test_session_date_hint(n, expected):
    assert parse_tcb_mail(_load(n), reference_date=_REFERENCE[n]).session_date_hint == expected


def test_future_corporate_calendar_dates_are_ignored():
    """Mail 1 names 23/9, 7/10, 8/10, 16/10 and 22/10 as upcoming corporate events.
    None may be mistaken for the session the mail describes."""
    p = parse_tcb_mail(_load(1), reference_date=_REFERENCE[1])
    assert p.session_date_hint <= _REFERENCE[1]


# ---------------------------------------------------------------------------
# Robustness — the parser never raises on a partial mail
# ---------------------------------------------------------------------------

def test_unknown_layout_yields_empty_extraction_not_an_error():
    p = parse_tcb_mail("Hello, this is not a TCBS mail at all.", reference_date=date(2026, 9, 22))
    assert p.vnindex_close is None
    assert p.companies == [] and p.recos == []


def test_empty_input_rejected():
    with pytest.raises(ValueError):
        parse_tcb_mail("   ")


def test_section3_only_paste_still_yields_the_recommendation():
    """The operator may paste just the part they care about."""
    p = parse_tcb_mail(
        "3. Khuyến nghị cổ phiếu\n\nHPG - Mua - Thép xây dựng phục hồi.\n",
        reference_date=date(2026, 9, 22),
    )
    assert [(r.symbol, r.action) for r in p.recos] == [("HPG", ACTION_BUY)]


def test_multiple_recommendations_in_one_mail():
    p = parse_tcb_mail(
        "3. Khuyến nghị cổ phiếu\n\n"
        "HPG - Mua - Lý do thứ nhất.\n\n"
        "VNM - Bán - Lý do thứ hai.\n\n"
        "FPT - Nắm giữ - Lý do thứ ba.\n",
        reference_date=date(2026, 9, 22),
    )
    assert [(r.symbol, r.action) for r in p.recos] == [
        ("HPG", ACTION_BUY), ("VNM", ACTION_SELL), ("FPT", ACTION_HOLD)]
    assert p.recos[0].rationale == "Lý do thứ nhất."
