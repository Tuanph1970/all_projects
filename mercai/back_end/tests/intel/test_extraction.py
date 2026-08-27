"""
Vietnamese price parsing and the extraction ladder.

The parser tests are the ones to keep: this is where quiet, systematic errors
live, and every case below is a real format seen on a Vietnamese storefront.
"""
from decimal import Decimal
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parents[2] / "services" / "intel"


@pytest.fixture()
def money(load_service):
    load_service(SERVICE)
    import app.services.money as money_module
    return money_module


@pytest.fixture()
def ladder(load_service):
    load_service(SERVICE)
    import app.services.extract as extract_module
    return extract_module


# --------------------------------------------------------------------------
# parse_vnd
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("1.250.000₫", 1_250_000),      # dot thousands, the VN default
    ("₫1,250,000", 1_250_000),      # comma thousands, prefix symbol
    ("1.250.000 đ", 1_250_000),
    ("185.000 đồng", 185_000),
    ("250000 VND", 250_000),
    ("185.000VNĐ", 185_000),
    ("250k", 250_000),              # shorthand, common in social commerce
    ("1,2 triệu", 1_200_000),
    ("1.2tr", 1_200_000),
    ("35 nghìn", 35_000),
    ("185000", 185_000),
    ("1.250", 1_250),               # VN reading: one thousand two hundred fifty
])
def test_real_vietnamese_price_formats(money, text, expected):
    assert money.parse_vnd(text) == Decimal(expected)


@pytest.mark.parametrize("text", [
    "0", "-5000", "2.000.000.000", "1.234,50", "", None, "liên hệ", "abc",
])
def test_values_that_must_not_be_trusted(money, text):
    """
    Refusing beats guessing. A missing price is a gap the seller can see; a
    wrong one is a pricing decision made on our say-so.
    """
    assert money.parse_vnd(text) is None


def test_a_discount_amount_is_not_a_price(money):
    """Stripping the minus would turn a saving into a competitor's price."""
    assert money.parse_vnd("-5000") is None
    assert money.parse_vnd("Giảm -50.000₫") is None


def test_a_range_string_is_ambiguous_and_refused(money):
    """
    `₫250.000 - ₫500.000` is two prices, so there is no single right answer and
    parse_vnd refuses it rather than inventing one. Ranges are handled a level
    up: the text rung's regex matches one currency-and-number pair at a time,
    and AggregateOffer markup carries lowPrice/highPrice explicitly.
    """
    assert money.parse_vnd("₫250.000 - ₫500.000") is None


def test_the_text_rung_reads_the_low_end_of_a_visible_range(money):
    """The minimum is what a buyer sees first, so that is what gets recorded."""
    match = money.VND_IN_TEXT.search("Giá: ₫250.000 - ₫500.000")
    assert money.parse_vnd(match.group(1) or match.group(2)) == Decimal(250_000)


def test_the_separator_trap(money):
    """
    `float("1.250.000")` raises and `float("1.250")` returns 1.25 -- an error of
    one thousand times that still looks like a plausible price in some other
    currency, and would sail through any range check written for VND.
    """
    assert money.parse_vnd("1.250.000") == Decimal(1_250_000)


def test_a_fractional_vnd_result_is_refused(money):
    """VND has no minor units; a fraction means the separator rule picked wrong."""
    assert money.parse_vnd("1.234,50") is None


def test_magnitude_check_needs_history_before_it_judges(money):
    assert money.is_plausible(185_000) is True
    assert money.is_plausible(185_000, [180_000, 190_000]) is True


def test_magnitude_check_catches_a_repointed_selector(money):
    """
    The failure mode most likely to survive every other guard: a site redesign
    moves a selector onto the wrong element, and the new number is well-formed
    and in range.
    """
    history = [180_000, 185_000, 190_000, 185_000]
    assert money.is_plausible(185_000, history) is True
    assert money.is_plausible(30_000_000, history) is False   # grabbed a bundle
    assert money.is_plausible(2_000, history) is False        # grabbed a shipping fee


# --------------------------------------------------------------------------
# The ladder
# --------------------------------------------------------------------------

JSONLD = (
    '<script type="application/ld+json">'
    '{"@type":"Product","name":"Bát men lam",'
    '"offers":{"@type":"Offer","price":"185000","priceCurrency":"VND"}}'
    '</script>'
)


def test_jsonld_is_read_and_titled(ladder):
    found = ladder.run_ladder(f"<html><head>{JSONLD}</head><body></body></html>")
    assert found.price == Decimal(185_000)
    assert found.tier == "jsonld"
    assert found.currency == "VND"
    assert found.title == "Bát men lam"


def test_agreement_across_rungs_promotes_confidence(ladder):
    html = (f'<html><head>{JSONLD}'
            '<meta property="product:price:amount" content="185000">'
            '</head><body><h1>x</h1><span>185.000₫</span></body></html>')
    found = ladder.run_ladder(html)
    assert found.confidence == 99
    assert found.flag.startswith("agrees")


def test_disagreement_downgrades_rather_than_picking_a_winner(ladder):
    """
    Two rungs disagreeing usually means a sale price against a list price --
    exactly the case where an alert must not fire.
    """
    html = (f'<html><head>{JSONLD}'
            '<meta property="product:price:amount" content="999000">'
            '</head><body></body></html>')
    found = ladder.run_ladder(html)
    assert found.price == Decimal(185_000)     # higher-precedence rung wins
    assert found.confidence == 70              # 95 - 25
    assert "tier_conflict" in found.flag


def test_a_struck_through_price_is_not_the_price(ladder):
    html = ('<html><body><h1>Bát</h1>'
            '<del>250.000₫</del><span>185.000₫</span></body></html>')
    found = ladder.run_ladder(html)
    assert found.price == Decimal(185_000)
    assert found.tier == "text"
    assert found.confidence == 55   # far below the alert threshold


def test_the_state_rung_skips_keys_that_are_not_the_price(ladder):
    html = ('<html><body><script id="__NEXT_DATA__">'
            '{"props":{"product":{"originalPrice":250000,"shippingFee":30000,'
            '"price":185000}}}</script></body></html>')
    found = ladder.run_ladder(html)
    assert found.price == Decimal(185_000)
    assert found.confidence <= 75, "a blind state walk must stay below the alert threshold"


def test_an_aggregate_offer_gives_a_range(ladder):
    from app.services.extract import jsonld
    html = ('<script type="application/ld+json">'
            '{"@type":"Product","offers":{"@type":"AggregateOffer",'
            '"lowPrice":"250000","highPrice":"500000","priceCurrency":"VND"}}'
            '</script>')
    low, high = jsonld.price_range(html)
    assert (low, high) == (Decimal(250_000), Decimal(500_000))
    # The minimum is what a buyer sees first and what a competitor is
    # effectively advertising.
    assert ladder.run_ladder(html).price == Decimal(250_000)


def test_nothing_found_returns_none(ladder):
    assert ladder.run_ladder("<html><body><p>Liên hệ để biết giá</p></body></html>") is None


def test_a_javascript_shell_is_distinguished_from_an_empty_page(ladder):
    shell = '<html><body><div id="__next"></div></body></html>'
    assert ladder.looks_javascript_rendered(shell, matched=False) is True
    assert ladder.looks_javascript_rendered(shell, matched=True) is False


def test_out_of_stock_is_read_from_the_offer(ladder):
    html = ('<script type="application/ld+json">'
            '{"@type":"Product","offers":{"price":"185000",'
            '"availability":"https://schema.org/OutOfStock"}}</script>')
    assert ladder.run_ladder(html).availability == "out_of_stock"


def test_a_broken_rung_does_not_kill_the_ladder(ladder, monkeypatch):
    """One bad extractor must not take the whole read down with it."""
    from app.services.extract import meta

    def boom(*a, **k):
        raise RuntimeError("selector engine exploded")

    monkeypatch.setattr(meta, "extract", boom)
    assert ladder.run_ladder(f"<html>{JSONLD}</html>").price == Decimal(185_000)
