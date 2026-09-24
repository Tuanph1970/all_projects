"""Rule-based extractor for the TCBS daily research email (FR-BM-EXTRACT).

The operator pastes the mail body into the React "TCB News" screen; this module splits
it into the `tcb_news` / `tcb_news_company` / `tcb_news_reco` shape. It is deliberately
deterministic and offline — no LLM, no network — so it unit-tests against stored
fixtures and a parser fix can be replayed over the archive. Raw text is always stored
alongside the extraction (EC-B2), so a field this parser misses is never lost.

Two languages share one mail template, and they disagree about separators: Vietnamese
writes 1.799,67 where English writes 1,816.93. Every number therefore crosses exactly
one conversion, `_num()`, which is told the language up front (EC-B5).

Nothing here raises on a missing field: an absent value is `None` and the operator sees
it as blank in the preview before confirming (EC-B10 applies to *promotion*, which is
the route's job, not the parser's).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Extracted shapes
# ---------------------------------------------------------------------------

# Normalised recommendation actions. WATCH is ours, not TCBS's: "Chờ mua" (wait to buy)
# is an explicit not-yet-a-buy — both sample mails carrying it also say "NĐT nên theo
# dõi thêm" — so folding it into BUY would overstate the desk (EC-B4 keeps the verbatim
# label beside the enum so the normalisation is never lossy).
ACTION_BUY = "BUY"
ACTION_SELL = "SELL"
ACTION_HOLD = "HOLD"
ACTION_WATCH = "WATCH"
ACTIONS = (ACTION_BUY, ACTION_SELL, ACTION_HOLD, ACTION_WATCH)

# Longest key first: "chờ mua" must beat "mua", "kém khả quan" must beat "khả quan".
_LABEL_MAP: dict[str, str] = {
    # WATCH — not yet a call to act
    "chờ mua": ACTION_WATCH,
    "cho mua": ACTION_WATCH,
    "canh mua": ACTION_WATCH,
    "chờ bán": ACTION_WATCH,
    "theo dõi": ACTION_WATCH,
    "quan sát": ACTION_WATCH,
    "wait to buy": ACTION_WATCH,
    "watch": ACTION_WATCH,
    "monitor": ACTION_WATCH,
    # SELL
    "kém khả quan": ACTION_SELL,
    "giảm tỷ trọng": ACTION_SELL,
    "underperform": ACTION_SELL,
    "reduce": ACTION_SELL,
    "bán": ACTION_SELL,
    "ban": ACTION_SELL,
    "sell": ACTION_SELL,
    # HOLD
    "nắm giữ": ACTION_HOLD,
    "nam giu": ACTION_HOLD,
    "trung lập": ACTION_HOLD,
    "duy trì": ACTION_HOLD,
    "neutral": ACTION_HOLD,
    "hold": ACTION_HOLD,
    # BUY
    "tăng tỷ trọng": ACTION_BUY,
    "mua ngay": ACTION_BUY,
    "khả quan": ACTION_BUY,
    "tích cực": ACTION_BUY,
    "outperform": ACTION_BUY,
    "accumulate": ACTION_BUY,
    "buy now": ACTION_BUY,
    "positive": ACTION_BUY,
    "mua": ACTION_BUY,
    "buy": ACTION_BUY,
    "add": ACTION_BUY,
}


@dataclass
class ParsedReco:
    """One row of section 3 — "NTP - Chờ mua - <rationale>"."""

    symbol: str
    action: Optional[str]          # normalised enum, None when the label is unknown
    label_verbatim: str            # exactly what TCBS wrote (EC-B4)
    rationale: Optional[str] = None
    target_price: Optional[float] = None


@dataclass
class ParsedCompany:
    """One "MSN: …" item of the Tin doanh nghiệp / Corporate News section."""

    symbol: str
    item_text: str


@dataclass
class ParsedMail:
    """Everything one pasted email yields. Every field is optional by design."""

    lang: str = "vi"
    session_date_hint: Optional[date] = None

    # Section 2 — Thị trường chung / General Market
    vnindex_close: Optional[float] = None
    vnindex_change_pct: Optional[float] = None
    vnindex_change_pts: Optional[float] = None
    matched_value_bn: Optional[float] = None
    matched_volume_m: Optional[float] = None
    putthrough_bn: Optional[float] = None
    total_value_bn: Optional[float] = None
    foreign_net_bn: Optional[float] = None
    foreign_buy_bn: Optional[float] = None
    foreign_sell_bn: Optional[float] = None
    foreign_top_buy: Optional[str] = None
    foreign_top_sell: Optional[str] = None
    foreign_ytd_net_bn: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    support_txt: Optional[str] = None
    resistance_txt: Optional[str] = None

    # Raw section text, kept verbatim so nothing the regexes miss is lost
    reports_txt: Optional[str] = None       # section 1, when present
    market_txt: Optional[str] = None
    liquidity_txt: Optional[str] = None
    foreign_txt: Optional[str] = None
    technical_txt: Optional[str] = None
    macro_domestic_txt: Optional[str] = None
    macro_intl_txt: Optional[str] = None

    companies: list[ParsedCompany] = field(default_factory=list)
    recos: list[ParsedReco] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

# U+2212 MINUS SIGN and the en/em dashes TCBS uses for negatives are not ASCII "-".
_MINUSES = {"−": "-", "–": "-", "—": "-", "‐": "-", "­": "-"}

_VI_MARKERS = ("Thị trường", "Khối ngoại", "Thanh khoản", "Kỹ thuật", "tỷ đồng",
               "Vĩ mô", "Khuyến nghị", "cổ phiếu", "Trong nước")


def detect_lang(text: str) -> str:
    """"vi" or "en". The mail is one language per send; we count VN-only markers
    rather than trusting the heading, because headings drift (the English mail titles
    section 3 "Recommendation", the Vietnamese one "Khuyến nghị cổ phiếu")."""
    hits = sum(1 for m in _VI_MARKERS if m in text)
    return "vi" if hits >= 2 else "en"


def _num(raw: Optional[str], lang: str) -> Optional[float]:
    """Parse one locale-formatted number. vi: 1.799,67 -> 1799.67. en: 1,816.93 -> 1816.93."""
    if raw is None:
        return None
    s = raw.strip()
    for bad, good in _MINUSES.items():
        s = s.replace(bad, good)
    s = s.replace(" ", "").replace(" ", "")
    if not s or not re.search(r"\d", s):
        return None
    neg = s.startswith("-")
    s = s.lstrip("+-")
    if lang == "vi":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if neg else val


# A locale-formatted number as it appears in the mail, sign included.
_NUMBER = r"[+\-−]?\d[\d.,]*"


def _find(pattern: str, text: Optional[str], group: int = 1) -> Optional[str]:
    if not text:
        return None
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return m.group(group) if m else None


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def normalize_action(label: str) -> Optional[str]:
    """Map TCBS's wording onto our four-value enum; None when unrecognised.

    Matching is accent-insensitive and longest-key-first, so "chờ mua" never degrades
    into "mua" and "kém khả quan" never degrades into "khả quan"."""
    if not label:
        return None
    probe = _strip_accents(label)
    for key in sorted(_LABEL_MAP, key=len, reverse=True):
        if _strip_accents(key) in probe:
            return _LABEL_MAP[key]
    return None


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

# Ordered anchors. Each is (name, regex). Section bodies run from the end of one
# anchor match to the start of the next anchor found *after* it — so a heading that
# is absent (sample 2 and 3 have no section 1) simply drops out.
_ANCHORS: list[tuple[str, str]] = [
    ("reports", r"^\s*1\.\s*(?:báo cáo phân tích|new analysis|analysis report)[^\n]*$"),
    ("section2", r"^\s*2\.\s*(?:cập nhật tin tức|market news)[^\n]*$"),
    ("general", r"^\s*(?:thị trường chung|general market)\s*$"),
    ("macro", r"^\s*(?:vĩ mô|macro(?:economics)?)\s*$"),
    ("corporate", r"^\s*(?:tin doanh nghiệp|corporate news)\s*$"),
    ("section3", r"^\s*3\.\s*(?:khuyến nghị|recommendation|stock recommendation)[^\n]*$"),
]

# Labelled paragraphs inside a section, e.g. "Khối ngoại: …".
_GENERAL_LABELS: list[tuple[str, str]] = [
    ("market", r"VN[\s\-–]?Index\s*:"),
    ("liquidity", r"(?:Thanh khoản|Liquidity)\s*:"),
    ("foreign", r"(?:Khối ngoại|Foreign trading|Foreign investors)\s*:"),
    ("technical", r"(?:Kỹ thuật|Technicals?)\s*:"),
]
_MACRO_LABELS: list[tuple[str, str]] = [
    ("domestic", r"(?:Trong nước|Domestic)\s*:"),
    ("international", r"(?:Quốc tế|International)\s*:"),
]


def _split_sections(text: str) -> dict[str, str]:
    """Slice the mail on its headings. Missing headings are simply absent from the result."""
    found: list[tuple[int, int, str]] = []
    for name, pat in _ANCHORS:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            found.append((m.start(), m.end(), name))
    found.sort()
    out: dict[str, str] = {}
    for i, (_start, end, name) in enumerate(found):
        stop = found[i + 1][0] if i + 1 < len(found) else len(text)
        out[name] = text[end:stop].strip()
    return out


def _split_labels(block: Optional[str], labels: list[tuple[str, str]]) -> dict[str, str]:
    """Same idea one level down: slice a section on its "Label:" paragraphs."""
    if not block:
        return {}
    found: list[tuple[int, int, str]] = []
    for name, pat in labels:
        m = re.search(pat, block, re.IGNORECASE)
        if m:
            found.append((m.start(), m.end(), name))
    found.sort()
    out: dict[str, str] = {}
    for i, (_start, end, name) in enumerate(found):
        stop = found[i + 1][0] if i + 1 < len(found) else len(block)
        out[name] = block[end:stop].strip()
    return out


# ---------------------------------------------------------------------------
# Session date
# ---------------------------------------------------------------------------

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def guess_session_date(text: str, reference: date) -> Optional[date]:
    """Best guess at the trading session the mail describes.

    The mail never states it outright, but it is always the newest date mentioned that
    has already happened — the macro paragraphs stamp it ("chiều 23/9 giờ Việt Nam",
    "the afternoon of 22 September"). Dates *after* `reference` are corporate-calendar
    items (SSB's 23/9–22/10 selling window, MWG's 7/10 ex-date) and are excluded, which
    is exactly what makes the rule work.

    This is a hint only: the operator confirms it in the preview before saving.
    """
    candidates: list[date] = []
    for d_s, m_s in re.findall(r"\b(\d{1,2})/(\d{1,2})\b", text):
        d_i, m_i = int(d_s), int(m_s)
        if not (1 <= d_i <= 31 and 1 <= m_i <= 12):
            continue
        for year in (reference.year, reference.year - 1):
            try:
                candidates.append(date(year, m_i, d_i))
            except ValueError:
                pass
    for d_s, mon in re.findall(r"\b(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\b", text, re.IGNORECASE):
        for year in (reference.year, reference.year - 1):
            try:
                candidates.append(date(year, _MONTHS[mon.lower()], int(d_s)))
            except ValueError:
                pass
    # Only dates already in the past relative to the paste, and not absurdly old.
    floor = reference - timedelta(days=45)
    past = [c for c in candidates if floor <= c <= reference]
    return max(past) if past else None


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

def _sentences(block: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", block) if s.strip()]


def _parse_market(out: ParsedMail, block: Optional[str], lang: str) -> None:
    """VN-Index close, and the change in points and percent.

    The percentage is printed unsigned with the direction carried by a verb ("Đánh mất
    0,88%" / "Posted a 0.96% rebound"), while the bracketed points figure is signed.
    We take the sign from the points and apply it to the percent — the two never
    disagree, and it beats keeping a list of Vietnamese verbs for "fell"."""
    if not block:
        return
    out.market_txt = block
    out.vnindex_change_pct = _num(_find(rf"({_NUMBER})\s*%", block), lang)
    out.vnindex_change_pts = _num(
        _find(rf"\(\s*({_NUMBER})\s*(?:điểm|points?)\s*\)", block), lang)
    out.vnindex_close = _num(
        _find(rf"(?:chốt phiên tại|close at|closed at|đóng cửa tại)\s*({_NUMBER})", block), lang)
    if out.vnindex_change_pct is not None and out.vnindex_change_pts is not None:
        if out.vnindex_change_pts < 0:
            out.vnindex_change_pct = -abs(out.vnindex_change_pct)
        else:
            out.vnindex_change_pct = abs(out.vnindex_change_pct)


def _parse_liquidity(out: ParsedMail, block: Optional[str], lang: str) -> None:
    if not block:
        return
    out.liquidity_txt = block
    out.matched_value_bn = _num(
        _find(rf"(?:khớp lệnh[^.]{{0,40}}?đạt|khớp lệnh[^.]{{0,40}}?ở mức|matched value[^.]{{0,40}}?"
              rf"(?:at|of))\s*(?:chỉ\s*|only\s*)?(?:VND\s*)?({_NUMBER})", block), lang)
    out.matched_volume_m = _num(
        _find(rf"({_NUMBER})\s*(?:triệu cổ phiếu|million shares)", block), lang)
    out.putthrough_bn = _num(
        _find(rf"(?:Tính cả|Including)\s*(?:VND\s*)?({_NUMBER})", block), lang)
    out.total_value_bn = _num(
        _find(rf"(?:tổng giá trị giao dịch đạt|total trading value reached|total trading value of)"
              rf"\s*(?:VND\s*)?({_NUMBER})", block), lang)


# Direction word immediately followed by its amount. Capturing the two together is the
# whole point: mail 2 reads "reversed to a modest net purchase of VND 54.1 billion …
# following heavy net selling in the previous session", so scanning the sentence for a
# direction word independently of the number flips a net buy into a net sell.
_FLOW_DIRECTION = (r"bán ròng|mua ròng|net (?:purchases?|buying|bought|sell(?:ing)?|sold|sales?)")
_FLOW = rf"({_FLOW_DIRECTION})\s*(?:of\s+)?(?:VND\s*)?({_NUMBER})"
_SELL_WORDS = re.compile(r"bán ròng|net (?:sell(?:ing)?|sold|sales?)", re.IGNORECASE)

# A ticker list runs to the clause break, not to the full stop: "…SSI và SHB, trong khi
# chiều mua ròng nghiêng về MCH…" puts both lists in one sentence.
_CLAUSE_END = r"(?=\s*,?\s*(?:trong khi|while|song|however)\b|\.\s|\.$|$)"


def _flow_amount(text: Optional[str], lang: str) -> Optional[float]:
    """Signed flow in VND bn: money leaving (bán ròng / net sold) is negative."""
    if not text:
        return None
    m = re.search(_FLOW, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    amount = _num(m.group(2), lang)
    if amount is None:
        return None
    return -abs(amount) if _SELL_WORDS.search(m.group(1)) else abs(amount)


def _parse_foreign(out: ParsedMail, block: Optional[str], lang: str) -> None:
    """Net foreign flow, signed: "bán ròng"/"net sold" is money leaving, so negative."""
    if not block:
        return
    out.foreign_txt = block
    sentences = _sentences(block)
    out.foreign_net_bn = _flow_amount(sentences[0] if sentences else block, lang)
    out.foreign_buy_bn = _num(
        _find(rf"(?:tổng giá trị mua|total purchases of|total purchases)\s*(?:VND\s*)?({_NUMBER})",
              block), lang)
    out.foreign_sell_bn = _num(
        _find(rf"(?:và bán|against sales of|sales of)\s*(?:VND\s*)?({_NUMBER})", block), lang)
    out.foreign_top_sell = _tickers(
        _find(r"(?:Lực bán tập trung tại|selling concentrated on|Net selling favoured)\s*(.+?)"
              + _CLAUSE_END, block))
    out.foreign_top_buy = _tickers(
        _find(r"(?:chiều mua ròng nghiêng về|Net buying favoured|net buying went to)\s*(.+?)"
              + _CLAUSE_END, block))
    ytd_clause = _find(r"(?:Lũy kế từ đầu năm|Year[ -]to[ -]date)\s*(.+?)(?=\.\s|\.$|$)", block)
    out.foreign_ytd_net_bn = _flow_amount(ytd_clause, lang)


# Currency codes and venue names match the ticker shape; they are never constituents.
_NOT_TICKERS = {"VND", "USD", "HSX", "HNX", "ETF", "HOSE", "YOY", "NDT"}


def _tickers(phrase: Optional[str]) -> Optional[str]:
    """"VHM, VIC, FPT, SSI và SHB" -> "VHM, VIC, FPT, SSI, SHB"."""
    if not phrase:
        return None
    found = [t for t in re.findall(r"\b([A-Z]{3}[A-Z0-9]?)\b", phrase) if t not in _NOT_TICKERS]
    return ", ".join(dict.fromkeys(found)) or None


def _parse_technical(out: ParsedMail, block: Optional[str], lang: str) -> None:
    if not block:
        return
    out.technical_txt = block
    for period in (5, 10, 20, 50):
        # "MA5 quanh 1.812 điểm" / "the MA5 around 1,813 points"
        val = _num(_find(rf"MA\s*{period}\b[^\d\n]{{0,24}}({_NUMBER})", block), lang)
        if val is not None:
            setattr(out, f"ma{period}", val)
    for sentence in _sentences(block):
        if out.support_txt is None and re.search(r"hỗ trợ|support", sentence, re.IGNORECASE):
            out.support_txt = sentence
        if out.resistance_txt is None and re.search(r"kháng cự|resistance", sentence, re.IGNORECASE):
            out.resistance_txt = sentence


# "MSN: Công bố kết quả…" — a ticker, a colon, then the item, to the end of the paragraph.
_COMPANY_ITEM = re.compile(r"^\s*([A-Z]{3}[A-Z0-9]?)\s*:\s*(.+?)\s*$", re.MULTILINE | re.DOTALL)


def _parse_companies(block: Optional[str]) -> list[ParsedCompany]:
    if not block:
        return []
    items: list[ParsedCompany] = []
    starts = [(m.start(), m.group(1)) for m in re.finditer(r"^\s*([A-Z]{3}[A-Z0-9]?)\s*:\s*",
                                                           block, re.MULTILINE)]
    for i, (pos, symbol) in enumerate(starts):
        head = re.match(r"^\s*[A-Z]{3}[A-Z0-9]?\s*:\s*", block[pos:])
        body_start = pos + (head.end() if head else 0)
        body_end = starts[i + 1][0] if i + 1 < len(starts) else len(block)
        text = " ".join(block[body_start:body_end].split())
        if text:
            items.append(ParsedCompany(symbol=symbol, item_text=text))
    return items


# "NTP - Chờ mua - Giá PVC tuần 14-18/9…". The label is bounded to 40 chars so the
# hyphens inside the rationale ("14-18/9") can never be mistaken for the separator.
_RECO_ITEM = re.compile(
    r"^\s*([A-Z]{3}[A-Z0-9]?)\s*[\-–—]\s*(.{1,40}?)\s*[\-–—]\s*(.+?)\s*$",
    re.MULTILINE | re.DOTALL,
)


def _parse_recos(block: Optional[str], lang: str) -> list[ParsedReco]:
    if not block:
        return []
    out: list[ParsedReco] = []
    starts = [m for m in re.finditer(r"^\s*([A-Z]{3}[A-Z0-9]?)\s*[\-–—]\s*(.{1,40}?)\s*[\-–—]\s*",
                                     block, re.MULTILINE)]
    for i, m in enumerate(starts):
        stop = starts[i + 1].start() if i + 1 < len(starts) else len(block)
        rationale = " ".join(block[m.end():stop].split()) or None
        label = " ".join(m.group(2).split())
        target = _num(_find(rf"(?:giá mục tiêu|target price)[^\d]{{0,20}}({_NUMBER})", rationale or ""), lang)
        out.append(ParsedReco(
            symbol=m.group(1),
            action=normalize_action(label),
            label_verbatim=label,
            rationale=rationale,
            target_price=target,
        ))
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_tcb_mail(raw: str, *, reference_date: Optional[date] = None) -> ParsedMail:
    """Split one pasted TCBS daily mail into the `tcb_news` shape.

    `reference_date` is the day the operator pasted the mail; it bounds the session-date
    guess (see `guess_session_date`) and defaults to today.
    """
    if raw is None:
        raise ValueError("raw mail content is required")
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ValueError("raw mail content is empty")

    lang = detect_lang(text)
    out = ParsedMail(lang=lang)
    out.session_date_hint = guess_session_date(text, reference_date or date.today())

    sections = _split_sections(text)
    out.reports_txt = sections.get("reports") or None

    general = _split_labels(sections.get("general"), _GENERAL_LABELS)
    _parse_market(out, general.get("market"), lang)
    _parse_liquidity(out, general.get("liquidity"), lang)
    _parse_foreign(out, general.get("foreign"), lang)
    _parse_technical(out, general.get("technical"), lang)

    macro = _split_labels(sections.get("macro"), _MACRO_LABELS)
    out.macro_domestic_txt = macro.get("domestic") or None
    out.macro_intl_txt = macro.get("international") or None

    out.companies = _parse_companies(sections.get("corporate"))
    out.recos = _parse_recos(sections.get("section3"), lang)
    return out
