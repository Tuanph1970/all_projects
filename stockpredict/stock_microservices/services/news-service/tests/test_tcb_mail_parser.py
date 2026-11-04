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


# ---------------------------------------------------------------------------
# Mail 4 — the 2026-11-03 paste, which drifted from the format mails 1-3 use
# ---------------------------------------------------------------------------
#
# WHY A FOURTH FIXTURE EXISTS. Mails 1-3 all phrase the net flow ADJACENTLY —
# "bán ròng 664,2 tỷ đồng" — so the old adjacency-only pattern matched them and
# the suite was green while `foreign_net_bn` was NULL on every mail the operator
# had actually stored. Those four real pastes interpose text: "Bán ròng PHIÊN
# THỨ NĂM LIÊN TIẾP VỚI GIÁ TRỊ 398,6 tỷ đồng" and "Bán ròng HƠN 500 tỷ đồng".
# The fixtures were unrepresentative in precisely the place that mattered, which
# is the only reason a field that never once worked looked tested.
#
# Mail 4 is terser than its predecessors throughout: a total trading value with
# no matched/put-through split, a semicolon between the two foreign ticker
# lists, a support level named without the word "hỗ trợ", and only three of the
# four moving averages given a number.


def test_mail4_total_value_survives_the_venue_and_the_hedge_word():
    """"Tổng giá trị giao dịch TRÊN HOSE đạt KHOẢNG 12.600 tỷ đồng".

    The old pattern wanted "tổng giá trị giao dịch đạt" contiguous, so the venue
    between the phrase and the verb, and "khoảng" between the verb and the
    number, were each enough to lose the figure.
    """
    r = parse_tcb_mail(_load(4))
    assert r.total_value_bn == pytest.approx(12600.0)


def test_mail4_reports_no_matched_split_because_the_mail_gives_none():
    """Not every NULL is a defect. This mail gives only a total, so matched
    value, matched volume and put-through are absent from the TEXT — inventing
    them would be worse than leaving them empty."""
    r = parse_tcb_mail(_load(4))
    assert r.matched_value_bn is None
    assert r.matched_volume_m is None
    assert r.putthrough_bn is None


def test_mail4_net_flow_is_read_through_the_hedge_word():
    """"Bán ròng HƠN 500 tỷ đồng" — negative, because selling is money leaving."""
    r = parse_tcb_mail(_load(4))
    assert r.foreign_net_bn == pytest.approx(-500.0)


def test_mail4_does_not_file_the_buyers_as_sellers():
    """THE DEFECT THAT MATTERED MOST, because it stored the opposite of the truth.

    The mail reads "...lực bán tập trung tại MBB và VCB; ở chiều ngược lại, HPG
    và SHB dẫn đầu danh sách mua ròng." The old clause-end set knew only
    "trong khi|while|song|however", so the sell capture ran past the SEMICOLON to
    the full stop and swallowed the buy tickers: the stored row read
    top_sell = "MBB, VCB, HPG, SHB" with top_buy empty.

    HPG and SHB were BOUGHT. A missing field is a gap; a field asserting the
    opposite direction is a lie, and anything reading it — a watchlist signal, a
    breadth measure — inherits the inversion silently.
    """
    r = parse_tcb_mail(_load(4))
    assert r.foreign_top_sell == "MBB, VCB"
    assert r.foreign_top_buy == "HPG, SHB"
    # Stated as the inversion itself, so a future delimiter change cannot
    # quietly re-merge the lists.
    assert "HPG" not in (r.foreign_top_sell or "")
    assert "SHB" not in (r.foreign_top_sell or "")


def test_mail4_buy_list_is_found_when_the_tickers_PRECEDE_the_phrase():
    """Mails 1-3 say "chiều mua ròng nghiêng về <tickers>"; mail 4 says
    "<tickers> dẫn đầu danh sách mua ròng". The follow-only pattern could not
    see the second construction at all."""
    r = parse_tcb_mail(_load(4))
    assert r.foreign_top_buy is not None
    assert r.foreign_top_buy.startswith("HPG")


def test_mail4_support_is_found_though_the_word_is_never_used():
    """"ngưỡng tâm lý 1.700 điểm là VÙNG CẦN LẤY LẠI gần nhất".

    A level to reclaim is a support level by another name. Requiring the literal
    "hỗ trợ" dropped the only downside reference in the mail.
    """
    r = parse_tcb_mail(_load(4))
    assert r.support_txt is not None
    assert "1.700" in r.support_txt


def test_mail4_moving_averages_stop_where_the_mail_stops():
    """The mail says "dưới cả BỐN đường trung bình động" but numbers only three.

    ma50 must stay None rather than borrow a number from the resistance range —
    an invented MA50 would read as a real level on the chart.
    """
    r = parse_tcb_mail(_load(4))
    assert r.ma5 == pytest.approx(1735)
    assert r.ma10 == pytest.approx(1747)
    assert r.ma20 == pytest.approx(1730)   # from the range "1.730 - 1.735"
    assert r.ma50 is None


def test_mail4_index_and_recommendation():
    r = parse_tcb_mail(_load(4))
    assert r.vnindex_close == pytest.approx(1699.62)
    assert r.vnindex_change_pct == pytest.approx(-0.65)
    assert r.vnindex_change_pts == pytest.approx(-11.10)
    assert len(r.recos) == 1
    reco = r.recos[0]
    assert reco.symbol == "SSI"
    assert reco.action == ACTION_WATCH
    assert "Chờ mua" in reco.label_verbatim
    assert len(r.companies) == 1 and r.companies[0].symbol == "DPR"


# ---------------------------------------------------------------------------
# The sign guarantee, kept while the adjacency rule was loosened
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n,expected", [(1, -664.2), (2, 54.1), (3, -1062.0), (4, -500.0)])
def test_net_flow_sign_is_governed_by_the_nearest_direction_word(n, expected):
    """Loosening adjacency must not reintroduce a sign inversion.

    Mail 2 is the dangerous one and it is why the old rule was tight: "reversed
    to a modest NET PURCHASE of VND 54.1 billion ... following heavy NET SELLING
    in the previous session". A scan that paired the amount with any nearby
    direction word would make that a net sale. The gap between direction and
    number may now contain words, but NOT another direction word, so the amount
    still belongs to the direction governing it.
    """
    assert parse_tcb_mail(_load(n)).foreign_net_bn == pytest.approx(expected)


def test_a_unit_is_required_so_a_session_count_cannot_become_an_amount():
    """"Bán ròng phiên thứ 5 liên tiếp với giá trị 398,6 tỷ đồng" — without the
    tỷ/billion requirement, "5" is the first number after the direction word and
    would be read as a 5-billion-dong net sale."""
    text = ("Khối ngoại: Bán ròng phiên thứ 5 liên tiếp với giá trị 398,6 tỷ đồng "
            "trên HoSE, gia tăng so với phiên trước.")
    r = parse_tcb_mail("Thị trường chung\n\nVN-Index: giảm.\n\n" + text)
    assert r.foreign_net_bn == pytest.approx(-398.6)


def test_an_amount_is_never_credited_to_a_direction_that_does_not_own_it():
    """THE SIGN GUARANTEE, and the case that actually exercises it.

    Mail 2 does not: there the amount sits immediately after its own direction
    word, so the guard is inert and a mutation removing it survived. The
    construction that needs it is one where the FIRST direction word carries no
    amount and a LATER one does:

        "Mua ròng trở lại sau khi bán ròng 500 tỷ đồng ở phiên trước."

    The 500 belongs to the SELLING. Without the negative lookahead the regex
    pairs the leading "Mua ròng" with it and reports +500 — a net purchase of
    half a trillion dong that never happened. With the lookahead the gap cannot
    span "bán ròng", so the match restarts there and the sign is right.
    """
    text = ("Thị trường chung\n\nVN-Index: giảm.\n\n"
            "Khối ngoại: Mua ròng trở lại sau khi bán ròng 500 tỷ đồng ở phiên trước.")
    assert parse_tcb_mail(text).foreign_net_bn == pytest.approx(-500.0)


def test_a_bare_semicolon_separates_the_two_ticker_lists():
    """The semicolon is a clause break in its own right.

    Mail 4 happens to follow its semicolon with "ở chiều ngược lại", so that
    connective alone would have fixed it — which left the semicolon untested and
    a mutation removing it survived. A mail that punctuates without the
    connective is just as plausible, and the sell list must still stop.
    """
    text = ("Thị trường chung\n\nVN-Index: giảm.\n\n"
            "Khối ngoại: Bán ròng 300 tỷ đồng trên HoSE, lực bán tập trung tại "
            "MBB và VCB; HPG và SHB dẫn đầu danh sách mua ròng.")
    r = parse_tcb_mail(text)
    assert r.foreign_top_sell == "MBB, VCB"
    assert "HPG" not in (r.foreign_top_sell or "")
    assert r.foreign_top_buy == "HPG, SHB"
