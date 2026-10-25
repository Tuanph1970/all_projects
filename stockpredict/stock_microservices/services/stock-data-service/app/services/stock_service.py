"""
Stock Service - Business logic for stock data operations
"""
import asyncio
import contextvars
import logging
import re
import time
from datetime import datetime, date, timedelta, time as dt_time
from typing import Optional, List, Tuple
import json
import pandas as pd

# Pandas 3.x removed applymap(); vnstock internally still uses it.
if not hasattr(pd.DataFrame, "applymap"):
    pd.DataFrame.applymap = pd.DataFrame.map  # type: ignore[attr-defined]

from vnstock import Vnstock
try:
    from vnai.beam.quota import RateLimitExceeded as _VnaiRateLimitExceeded
except Exception:
    _VnaiRateLimitExceeded = None

from app.config import get_settings
from app.models.domain import Company, StockPrice, Industry, PriceBoard, CompanyProfile, FinancialStatement
from app.models.schemas import (
    CompanyResponse,
    CompanyDetailResponse,
    CompanyListingResponse,
    StockPriceResponse,
    HistoricalDataResponse,
    TopMoverResponse,
    SearchResult,
    MarketIndexResponse,
    IndustryResponse,
    PaginatedResponse,
    CompanyFinancialsResponse,
    FinancialRatiosData,
    GrowthMetricsData,
    IncomeStatementData,
    BalanceSheetData,
    CashFlowData,
)
from app.repositories.stock_repository import StockRepository


settings = get_settings()
logger = logging.getLogger(__name__)

#: Our API's period vocabulary -> vnstock's.
#:
#: These are NOT the same words, and vnstock does not complain. Handed
#: `period="annual"` it silently returns QUARTERLY data whose column labels
#: all collapse to one year:
#:
#:     period="annual"  ->  (25, 19), year columns ['2026'] x 16
#:     period="year"    ->  (25,  7), year columns ['2025','2024','2023','2022']
#:
#: `to_dict(orient="records")` then keeps one value per repeated key, so
#: sixteen quarterly columns became a single '2026' — and for `ratio` every
#: column was labelled '2018', so the served figures were eight years stale.
#: Downstream, ai-insights' long-term recommender scores *consecutive years*
#: of P/E improvement and profit growth; given one year it scored nothing and
#: returned an empty list, which is why the dashboard showed N/A.
#:
#: Nothing raised at any point. An unrecognised period is therefore refused
#: here rather than forwarded.
VNSTOCK_PERIODS = {
    "annual": "year",
    "year": "year",
    "quarter": "quarter",
}

#: Backlog #95a — per-statement source, because VCI's `ratio()` is corrupted.
#:
#: Measured on FPT 2026-10-23:
#:   VCI ratio          (54, 19)  16 periods ALL labelled 2018, the values
#:                                being 4 genuine periods repeated 4x
#:   KBS ratio          (58,  6)  4 clean years, with pe_ratio, roe and
#:                                book_value_per_share_bvps (closes #76)
#:   KBS balance_sheet  (0,  0)   EMPTY
#:
#: So this is deliberately per-statement rather than a wholesale switch: a
#: wholesale switch to KBS would silently lose the balance sheet.
FINANCIAL_SOURCE_OVERRIDES = {"ratio": "KBS"}


#: Backlog #97 — our response field -> (KBS `item_id`, scale).
#:
#: VCI's `ratio()` is degenerate: `period="quarter"` returns columns labelled
#: 2018-Q1..Q4 and `period="year"` sixteen columns all labelled 2018, BOTH
#: carrying the same four numbers. FPT's served `pe_ratio` was 11.6044 — one
#: of them — against an actual FY2025 15.91. Fifteen fields were present,
#: plausible and eight years stale.
#:
#: ANNUAL, decided by measurement: KBS `period="year"` is (58, 6) with four
#: distinct ordered years, while `period="quarter"` returns columns
#: `2026-Q2, 2025-Q4, 2026-Q1, 2025-Q4_1` — unordered, with FPT's
#: `2025-Q4_1` duplicating *2026-Q2's* values, and quarterly ROE reading 5.89
#: against an annual 28.3 (un-annualised). Three traps in one frame.
#:
#: `scale` converts KBS's convention to the one the response already uses:
#:   "as_is"    both agree (plain multiples, and percents the code already
#:              normalised to percent for VCI via `_as_percent`)
#:   "from_pct" KBS reports a percent where the response carries a multiple
KBS_RATIO_FIELDS = {
    "pe_ratio":         ("pe_ratio", "as_is"),
    "pb_ratio":         ("pb_ratio", "as_is"),
    "ps_ratio":         ("ps_ratio", "as_is"),
    "ev_ebitda":        ("ev_ebitda", "as_is"),
    "roe":              ("roe", "as_is"),
    "roa":              ("roa", "as_is"),
    "gross_margin":     ("gross_margin", "as_is"),
    "operating_margin": ("ebit_margin", "as_is"),
    "profit_margin":    ("net_margin", "as_is"),
    "dividend_yield":   ("dividend_yield", "as_is"),
    "current_ratio":    ("short_term_ratio", "as_is"),
    "quick_ratio":      ("quick_ratio", "as_is"),
    # TOTAL liabilities over equity, as a MULTIPLE — the faithful analogue of
    # VCI's field (0.7994 for FPT). KBS's own `debt_to_equity` (48.17) is
    # interest-bearing debt ONLY and is a percent, so taking it would both
    # change the definition and publish 48.17x gearing.
    "debt_to_equity":   ("liabilities_to_equity", "from_pct"),
}

#: Deliberately NOT sourced here:
#:   market_cap        — KBS's ratio sheet has none, and VCI's was ~3x stale
#:                       (26.57T against roughly 84T for FPT). Absent beats
#:                       wrong, which is how #76 was decided.
#:   debt_to_assets    — DERIVED from the balance sheet at #76/#77, not from
#:   enterprise_value    the ratio sheet, so #97 does not touch either.
#:   eps               — comes from the income statement.


def ratio_metrics_from_kbs(df):
    """Normalised ratio metrics and the period they describe, from a KBS frame.

    Returns `({field: value}, as_of)` — `({}, None)` when the frame is not a
    usable KBS ratio sheet.

    **The period matters and is returned, not assumed.** KBS annual
    price-based ratios (P/E, P/B, P/S, EV/EBITDA, dividend yield) are priced
    at FISCAL YEAR END, not today. Measured: deriving price as `BVPS x P/B`
    lands within 2% for TCB and 6% for VNM but 68% out for FPT, whose price
    fell from ~96k to 57k during 2025. So `as_of` travels with the numbers
    rather than leaving a consumer to assume they are current.
    """
    import pandas as _pd

    empty = ({}, None)
    if df is None or not isinstance(df, _pd.DataFrame) or df.empty:
        return empty
    if "item_id" not in df.columns:
        return empty

    # A period label is exactly four digits, optionally with a quarter part.
    # `2025_1` is a de-duplicated duplicate, not a period (see the quarterly
    # frame's `2025-Q4_1`), and must never be mistaken for one.
    periods = [c for c in df.columns
               if str(c)[:4].isdigit() and "_" not in str(c)]
    if not periods:
        return empty
    latest = sorted(periods, key=str, reverse=True)[0]

    by_id = {}
    for _, row in df.iterrows():
        key = str(row.get("item_id"))
        if key and key not in by_id:
            by_id[key] = row.get(latest)

    out = {}
    for field, (item_id, scale) in KBS_RATIO_FIELDS.items():
        raw = by_id.get(item_id)
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value != value:                      # NaN
            continue
        out[field] = value / 100.0 if scale == "from_pct" else value

    return out, (str(latest) if out else None)


def bvps_from_ratio_frame(df) -> Optional[float]:
    """Book value per share from a KBS ratio frame, or `None`.

    Backlog #76. The field has been absent since the 4.x rewrite, and the
    earlier investigation was right to leave it absent: it probed VCI under
    five candidate names and found none, and refused to derive it from
    `(pe x eps) / pb` because `eps` is quarterly while `P/E` is trailing, so
    the implied price — and the book value falling out of it — would be wrong
    by roughly 4x. A wrong book value is worse than an absent one.

    What changed is the SOURCE. `#95a` moved the statement `ratio` call to KBS
    because VCI's is corrupted, and the KBS sheet carries
    `book_value_per_share_bvps` outright. So this reads it; it does not
    compute it.

    Keyed on `item_id`, not on a display label: `item_id` is the stable
    identifier, and KBS supplies no `item_en` at all (which is why
    `_latest_metrics` cannot be pointed at a KBS frame as it stands).

    Declines a non-numeric or non-positive value rather than publishing it —
    the same principle as refusing the derivation.
    """
    import pandas as _pd

    if df is None or not isinstance(df, _pd.DataFrame) or df.empty:
        return None
    if "item_id" not in df.columns:
        return None

    periods = [c for c in df.columns if str(c)[:4].isdigit()]
    if not periods:
        return None
    # KBS's annual frame is newest-first; sort defensively so an ordering
    # change cannot silently hand back an older year.
    latest = sorted(periods, key=lambda c: str(c), reverse=True)[0]

    for _, row in df.iterrows():
        if str(row.get("item_id")) != "book_value_per_share_bvps":
            continue
        try:
            value = float(row.get(latest))
        except (TypeError, ValueError):
            return None
        if not (value > 0):
            return None
        return value
    return None

#: KBS rejects `lang` outright (`Finance.ratio() got an unexpected keyword
#: argument 'lang'`), so the keyword set is per-source too. The cost is only
#: the English `item_en` label; `item_id` is the stable key and the one
#: consumers read.
SOURCE_SUPPORTS_LANG = {"VCI": True, "KBS": False}

#: Dividends (#59). No vnstock 4.0.7 source exposes Company.dividends(), but
#: VCI's corporate-events feed carries them: DIV rows are cash dividends and
#: some ISS rows are share distributions. VCI tags every DIV/ISS row
#: category=DIVIDEND (ESOP and rights issues included), so the English title
#: is the only discriminator. Order matters: first match wins.
DIVIDEND_SHARE_ISSUE_KINDS = (
    ("stock dividend", "Cổ tức bằng cổ phiếu", "Stock"),
    ("bonus issue", "Cổ phiếu thưởng", "Bonus shares"),
)
#: Public Company.events() fetches ONE page of 50 across every event type,
#: so director dealings crowd dividends out; page through DIV,ISS directly.
DIVIDEND_EVENTS_PAGE_SIZE = 200
DIVIDEND_EVENTS_MAX_PAGES = 10
DIVIDEND_EVENTS_FROM_DATE = "20000101"

#: Price board staleness (#48). HOSE/HNX trade Mon-Fri 09:00-15:00 ICT (ATC
#: ends 14:45; 15:00 covers HNX's post-close session). Vietnam has no DST, so
#: a fixed UTC+7 offset is exact. Holidays are not modelled: on one, the board
#: just refetches an unchanged market at most once per max-age.
MARKET_TZ_OFFSET = timedelta(hours=7)
MARKET_OPEN = dt_time(9, 0)
MARKET_CLOSE = dt_time(15, 0)


def _utcnow() -> datetime:
    """Naive UTC, matching how PriceBoard.updated_at is stored. Patched in tests."""
    return datetime.utcnow()


def price_board_is_stale(updated_at: Optional[datetime], now: datetime, max_age: timedelta) -> bool:
    """Whether a board snapshot taken at ``updated_at`` (naive UTC) is stale at ``now``.

    In session: older than ``max_age``. Outside it: taken before the most
    recent close, i.e. it does not show the last session's final prices.
    """
    if updated_at is None:
        return True
    local_now = now + MARKET_TZ_OFFSET
    if local_now.weekday() < 5 and MARKET_OPEN <= local_now.time() < MARKET_CLOSE:
        return now - updated_at > max_age
    last_close = datetime.combine(local_now.date(), MARKET_CLOSE)
    if local_now < last_close:
        last_close -= timedelta(days=1)
    while last_close.weekday() >= 5:
        last_close -= timedelta(days=1)
    return updated_at + MARKET_TZ_OFFSET < last_close


# One refresh per group at a time; concurrent readers wait, then see fresh rows.
_price_board_locks: dict = {}
_price_board_lock_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_price_board_lock(group: str) -> asyncio.Lock:
    """Per-group lock, reset if the running loop changes (see _get_vnstock_lock)."""
    global _price_board_lock_loop
    loop = asyncio.get_running_loop()
    if _price_board_lock_loop is not loop:
        _price_board_locks.clear()
        _price_board_lock_loop = loop
    return _price_board_locks.setdefault(group, asyncio.Lock())


def _is_rate_limit(exc: Exception) -> bool:
    return _VnaiRateLimitExceeded is not None and isinstance(exc, _VnaiRateLimitExceeded)


# vnstock 4.x enforces a per-process quota (vnai: 20 req/min guest, 60 with a
# free key). One lock + timestamp for the whole process so every caller —
# request handlers and the nightly sync alike — shares the same budget.
_vnstock_call_lock: Optional[asyncio.Lock] = None
_vnstock_lock_loop: Optional[asyncio.AbstractEventLoop] = None
_vnstock_last_call: float = 0.0
# True inside the nightly sync task: its calls give the next quota slot away
# (sleep one interval *after* releasing the lock) so interactive requests are
# not queued FIFO behind ~240 sync calls.
vnstock_background: contextvars.ContextVar[bool] = contextvars.ContextVar("vnstock_background", default=False)


def _get_vnstock_lock() -> asyncio.Lock:
    """Process-wide lock, recreated if the running loop changes (an
    asyncio.Lock binds to the loop that first awaits it)."""
    global _vnstock_call_lock, _vnstock_lock_loop
    loop = asyncio.get_running_loop()
    if _vnstock_call_lock is None or _vnstock_lock_loop is not loop:
        _vnstock_call_lock = asyncio.Lock()
        _vnstock_lock_loop = loop
    return _vnstock_call_lock


def adjusted_close(row) -> Optional[float]:
    """The adjusted close for one vnstock row.

    vnstock/VCI returns a back-adjusted series — its OHLCV column map is exactly
    time/open/high/low/close/volume with no separate adjusted field, and a share-count
    event restates the whole prior history (verified against TCB's 1:1 bonus issue,
    ex-date June 2024, whose series is continuous at the post-bonus level). So `close`
    IS the adjusted close and this mirrors it.

    Writing it rather than leaving NULL is the point (Backlog #56): a NULL adj_close
    reads as "prices are unadjusted" to anything computing a return, which is the
    opposite of the truth and had already produced a false warning downstream.

    A future source that does expose an explicit adjusted column is picked up here
    without touching either call site.
    """
    for key in ("adj_close", "adjusted_close", "adjClose"):
        value = row.get(key)
        if value is not None:
            return float(value)
    close = row.get("close")
    return float(close) if close is not None else None


async def vnstock_call(fn, *args, **kwargs):
    """Run a blocking vnstock call in a worker thread, spaced so we stay
    under vnai's per-minute quota. If the quota is hit anyway, honour
    vnai's ``retry_after`` once before giving up.
    """
    global _vnstock_last_call
    min_interval = settings.vnstock_min_interval
    try:
        async with _get_vnstock_lock():
            for attempt in (1, 2):
                wait = _vnstock_last_call + min_interval - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                _vnstock_last_call = time.monotonic()
                try:
                    return await asyncio.to_thread(fn, *args, **kwargs)
                except Exception as e:
                    if attempt == 2 or not settings.VNSTOCK_RATE_LIMIT_RETRY or not _is_rate_limit(e):
                        raise
                    retry_after = getattr(e, "retry_after", None) or min_interval
                    retry_after = min(float(retry_after), settings.VNSTOCK_RATE_LIMIT_MAX_WAIT_SECONDS)
                    logger.warning(
                        f"vnstock rate limit hit ({getattr(e, 'tier', '?')} tier) — "
                        f"waiting {retry_after:.0f}s then retrying once"
                    )
                    await asyncio.sleep(retry_after)
                    _vnstock_last_call = 0.0
    finally:
        if vnstock_background.get():
            await asyncio.sleep(min_interval)


class StockService:
    """Service for stock data operations"""

    def __init__(self, repository: StockRepository):
        self.repository = repository
        self._vnstock = None

    @property
    def vnstock(self) -> Vnstock:
        """Lazy load VNStock client"""
        if self._vnstock is None:
            self._vnstock = Vnstock(source=settings.VNSTOCK_DATA_SOURCE)
        return self._vnstock

    # ==================== Company Operations ====================

    async def get_all_companies(
        self,
        page: int = 1,
        page_size: int = 50,
        exchange: Optional[str] = None,
        industry_id: Optional[int] = None,
    ) -> Tuple[List[CompanyResponse], int, int]:
        """Get all companies with pagination"""
        skip = (page - 1) * page_size
        companies, total = await self.repository.get_all_companies(
            skip=skip,
            limit=page_size,
            exchange=exchange,
            industry_id=industry_id,
        )

        # If database is empty, fallback to live data from vnstock
        if total == 0 and not exchange and not industry_id:
            logger.info("Database empty, fetching live company data from vnstock")
            live_companies = await self.get_all_companies_live()
            total = len(live_companies)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            # Paginate live data
            paginated = live_companies[skip:skip + page_size]

            responses = [
                CompanyResponse(
                    id=0,
                    symbol=c.symbol,
                    name=c.name,
                    name_en=None,
                    exchange=c.exchange,
                    industry_id=None,
                    industry_name=None,
                    listing_date=None,
                    outstanding_shares=None,
                    market_cap=None,
                    website=None,
                    description=None,
                    is_active=True,
                    is_tradeable=True,
                )
                for c in paginated
            ]
            return responses, total, total_pages

        total_pages = (total + page_size - 1) // page_size

        responses = [
            CompanyResponse(
                id=c.id,
                symbol=c.symbol,
                name=c.name,
                name_en=c.name_en,
                exchange=c.exchange,
                industry_id=c.industry_id,
                industry_name=c.industry.name if c.industry else None,
                listing_date=c.listing_date,
                outstanding_shares=c.outstanding_shares,
                market_cap=c.market_cap,
                website=c.website,
                description=c.description,
                is_active=c.is_active,
                is_tradeable=c.is_tradeable,
            )
            for c in companies
        ]

        return responses, total, total_pages

    async def get_company_detail(self, symbol: str) -> Optional[CompanyDetailResponse]:
        """Get detailed company information"""
        company = await self.repository.get_company_by_symbol(symbol)
        if not company:
            return None

        # Get latest price
        latest_price = await self.repository.get_latest_price(company.id)

        industry_response = None
        if company.industry:
            industry_response = IndustryResponse(
                id=company.industry.id,
                code=company.industry.code,
                name=company.industry.name,
                name_en=company.industry.name_en,
                description=company.industry.description,
                level=company.industry.level,
            )

        return CompanyDetailResponse(
            id=company.id,
            symbol=company.symbol,
            name=company.name,
            name_en=company.name_en,
            exchange=company.exchange,
            industry=industry_response,
            listing_date=company.listing_date,
            outstanding_shares=company.outstanding_shares,
            market_cap=company.market_cap,
            website=company.website,
            description=company.description,
            current_price=latest_price.close if latest_price else None,
            change=latest_price.change if latest_price else None,
            change_percent=latest_price.change_percent if latest_price else None,
            volume=latest_price.volume if latest_price else None,
        )

    async def search_companies(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Search companies by symbol or name"""
        companies = await self.repository.search_companies(query, limit)

        return [
            SearchResult(
                symbol=c.symbol,
                name=c.name,
                exchange=c.exchange,
                industry_name=c.industry.name if c.industry else None,
                match_score=1.0 if c.symbol.upper() == query.upper() else 0.5,
            )
            for c in companies
        ]

    # ==================== Live Company Data from VNStock ====================

    async def get_all_companies_live(self) -> List[CompanyListingResponse]:
        """
        Get all companies from vnstock (live data).
        This fetches directly from vnstock API, not from database.
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)
            df = await vnstock_call(stock.listing.all_symbols)

            if df is None or df.empty:
                logger.warning("No companies returned from vnstock")
                return []

            companies = [
                CompanyListingResponse(
                    symbol=row["symbol"],
                    name=row.get("organ_name", row.get("organName", "")),
                    exchange=None,  # all_symbols doesn't provide exchange
                )
                for _, row in df.iterrows()
            ]

            logger.info(f"Fetched {len(companies)} companies from vnstock")
            return companies

        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(f"vnstock rate limit hit fetching company list — retry later")
            else:
                logger.error(f"Error fetching companies from vnstock: {e}")
            return []

    async def get_companies_by_group_live(self, group: str = "VN30") -> List[CompanyListingResponse]:
        """
        Get companies by stock group from vnstock (live data).

        Args:
            group: Stock group (VN30, VN100, HOSE, HNX, UPCOM, etc.)
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)

            # symbols_by_group returns a Series, not DataFrame
            symbols = await vnstock_call(stock.listing.symbols_by_group, group.upper())

            if symbols is None or len(symbols) == 0:
                logger.warning(f"No companies returned for group {group}")
                return []

            # Convert Series to list of CompanyListingResponse
            companies = [
                CompanyListingResponse(
                    symbol=symbol,
                    name="",  # symbols_by_group only returns symbols, not names
                    exchange=group.upper() if group.upper() in ["HOSE", "HNX", "UPCOM"] else None,
                )
                for symbol in symbols
            ]

            logger.info(f"Fetched {len(companies)} companies for group {group}")
            return companies

        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(f"vnstock rate limit hit fetching group {group} — retry later")
            else:
                logger.error(f"Error fetching companies by group {group}: {e}")
            return []

    async def search_companies_live(self, query: str, limit: int = 20) -> List[CompanyListingResponse]:
        """
        Search companies from vnstock (live data).
        Searches through all listed companies by symbol or name.
        """
        try:
            # Get all companies first
            all_companies = await self.get_all_companies_live()

            if not all_companies:
                return []

            query_upper = query.upper()
            query_lower = query.lower()

            # Filter by symbol or name match
            matched = []
            for company in all_companies:
                symbol_match = query_upper in company.symbol.upper()
                name_match = query_lower in company.name.lower() if company.name else False

                if symbol_match or name_match:
                    matched.append(company)

                if len(matched) >= limit:
                    break

            return matched

        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []

    # ==================== Company Info (Profile/News/Events/Dividends) ====================

    # Column mappings: VCI snake_case → frontend camelCase (matching legacy webapi)
    # Legacy (vnstock 3.x) and current (vnstock 4.x / VCI) overview() column
    # names, both mapped to the camelCase keys the rest of the code reads.
    # 4.x dropped history / icb_name* / charter_capital / no_employees and
    # emits `issue_share` several times, so callers must _dedupe_columns first.
    OVERVIEW_COLUMN_MAP = {
        'symbol': 'ticker', 'issue_share': 'issueShare',
        'company_profile': 'companyProfile', 'history': 'history',
        'icb_name2': 'industry', 'icb_name3': 'industryL2', 'icb_name4': 'industryL3',
        'charter_capital': 'charterCapital', 'no_employees': 'noEmployees',
        'no_shareholders': 'noShareholders', 'foreign_percent': 'foreignPercent',
        'outstanding_share': 'outstandingShare', 'free_float_rate': 'freeFloatRate',
        # vnstock 4.x
        'sector': 'industry',
        'foreigner_percentage': 'foreignPercent',
        'free_float_percentage': 'freeFloatRate',
    }

    # Financial statement column maps: vnstock English column → frontend snake_case key.
    # Uses partial matching so minor vnstock version changes (e.g. added units) still work.
    INCOME_STATEMENT_MAP = {
        'yearReport': 'report_year', 'lengthReport': 'length_report',
        'Revenue (Bn. VND)': 'revenue', 'Revenue YoY': 'revenue_yoy',
        'Net Sales': 'sales', 'Cost of Sales': 'cost_of_sales',
        'Gross Profit': 'gross_profit', 'Selling Expenses': 'selling_expenses',
        'General & Admin': 'admin_expenses', 'Operating Profit': 'operating_profit',
        'Financial Income': 'financial_income', 'Financial Expenses': 'financial_expenses',
        'Interest Expenses': 'interest_expenses',
        'Profit before tax': 'profit_before_tax',
        'Net Profit For the Year': 'net_profit_for_the_year',
        'Attributable to parent': 'net_profit',
        'Attribute to parent company YoY': 'net_profit_yoy',
        'Minority Interest': 'minority_interest',
        'EPS': 'eps_basis',
    }

    CASH_FLOW_MAP = {
        'yearReport': 'report_year', 'lengthReport': 'length_report',
        'Net cash inflows/outflows from operating': 'cash_from_operating_activities',
        'Net Cash Flows from Investing': 'cash_from_investing_activities',
        'Cash flows from financial': 'cash_from_financing_activities',
        'Net increase/decrease in cash': 'net_change_in_cash',
        'Cash and cash equivalents': 'cash',
        'Cash and Cash Equivalents at the end': 'cash_end_of_period',
        'Dividends paid': 'dividends_paid',
        'Gain on Dividend': 'gain_on_dividend',
        'Increase in charter': 'increase_in_charter_captial',
        'Purchase of fixed assets': 'purchase_fixed_assets',
        'Proceeds from borrowings': 'proceeds_from_borrowings',
        'Repayment of borrowings': 'repayment_of_borrowings',
        'Depreciation and Amortisation': 'depreciation_amortisation',
    }

    BALANCE_SHEET_MAP = {
        'yearReport': 'report_year', 'lengthReport': 'length_report',
        'CURRENT ASSETS': 'current_assets',
        'Cash and cash equivalents': 'cash',
        'Short-term investments': 'short_term_investments',
        'Accounts receivable': 'accounts_receivable',
        'Net Inventories': 'net_inventories',
        'LONG-TERM ASSETS': 'long_term_assets',
        'Fixed assets': 'fixed_assets',
        'TOTAL ASSETS': 'total_assets',
        'LIABILITIES': 'total_liabilities',
        'Current liabilities': 'current_liabilities',
        'Long-term liabilities': 'long_term_liabilities',
        "OWNER'S EQUITY": 'owners_equity',
        'Capital and reserves': 'capital_and_reserves',
        'Undistributed earnings': 'undistributed_earnings',
        'TOTAL RESOURCES': 'total_resources',
        'MINORITY INTERESTS': 'minority_interests',
    }

    RATIO_MAP = {
        'yearReport': 'metayearreport',
        'P/E': 'p_e', 'P/B': 'p_b', 'P/S': 'p_s',
        'P/Cash Flow': 'p_cash_flow',
        'EPS (VND)': 'eps', 'BVPS (VND)': 'bvps',
        'ROE (%)': 'roe', 'ROA (%)': 'roa', 'ROIC (%)': 'roic',
        'Market Capital': 'market_capital',
        'Debt/Equity': 'debt_to_equity',
        'Current Ratio': 'current_ratio', 'Quick Ratio': 'quick_ratio',
        'Cash Ratio': 'cash_ratio',
        'Gross Profit Margin': 'gross_margin',
        'Net Profit Margin': 'net_margin',
        'EBIT Margin': 'ebit_margin',
        'Dividend yield': 'dividend_yield',
        'EV/EBITDA': 'ev_ebitda',
        'Outstanding Share': 'outstanding_share',
        'Interest Coverage': 'interest_coverage',
        'Asset Turnover': 'asset_turnover',
    }

    FINANCIAL_STATEMENT_MAPS = {
        'income_statement': INCOME_STATEMENT_MAP,
        'cash_flow': CASH_FLOW_MAP,
        'balance_sheet': BALANCE_SHEET_MAP,
        'ratio': RATIO_MAP,
    }

    NEWS_COLUMN_MAP = {
        'ticker': 'symbol', 'news_title': 'title',
        'news_short_content': 'description', 'news_full_content': 'content',
        'news_source_link': 'source', 'news_image_url': 'imageUrl',
        'public_date': 'publishDate', 'created_at': 'createdAt',
        'close_price': 'price', 'ref_price': 'referencePrice',
        'price_change_pct': 'changePercent', 'floor': 'floorPrice', 'ceiling': 'ceilingPrice',
    }

    EVENTS_COLUMN_MAP = {
        'ticker': 'symbol', 'event_title': 'title',
        'event_list_name': 'eventType', 'en__event_list_name': 'eventTypeEn',
        'public_date': 'publishDate', 'issue_date': 'issueDate',
        'record_date': 'recordDate', 'exright_date': 'exrightDate',
        'source_url': 'source', 'ratio': 'ratio', 'value': 'value',
    }

    @staticmethod
    def _dedupe_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Keep the first of any repeated column. vnstock 4.x overview()
        returns `issue_share` four times; with duplicates, row.get(name)
        yields a Series and `pd.notna(...)` in an `if` raises."""
        return df.loc[:, ~df.columns.duplicated()]

    @staticmethod
    def _first_value(row: pd.Series, *keys, default=None):
        """First non-null scalar among `keys` in `row` (tolerates missing keys)."""
        for key in keys:
            if key not in row.index:
                continue
            value = row[key]
            if isinstance(value, pd.Series):
                value = value.iloc[0] if len(value) else None
            if value is not None and not (pd.api.types.is_scalar(value) and pd.isna(value)):
                return value
        return default

    @staticmethod
    def _standardize_df(df: pd.DataFrame, column_map: dict, convert_dates: bool = False) -> pd.DataFrame:
        """Rename columns and optionally convert millisecond timestamps to ISO strings."""
        if convert_dates:
            for col in ['public_date', 'created_at', 'updated_at']:
                if col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col], unit='ms', errors='coerce')
                        df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass
        rename_map = {old: new for old, new in column_map.items() if old in df.columns}
        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    async def get_company_profile_data(self, symbol: str) -> List[dict]:
        """Get company overview/profile data from vnstock.

        Enriches the base overview with trading_stats() for foreign ownership
        and shareholders() for shareholder count, since overview() no longer
        returns these fields in the VCI data source.
        """
        try:
            stock = self.vnstock.stock(symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE)
            df = await vnstock_call(stock.company.overview)

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return []

            # overview() may return a DataFrame or a Series; normalise to DataFrame
            if isinstance(df, pd.Series):
                df = df.to_frame().T

            df = self._dedupe_columns(df)
            df = self._dedupe_columns(self._standardize_df(df, self.OVERVIEW_COLUMN_MAP))

            # Enrich with trading_stats() for foreign ownership data
            try:
                ts_df = await vnstock_call(stock.company.trading_stats)
                if ts_df is not None and not ts_df.empty:
                    ts_row = self._dedupe_columns(ts_df).iloc[0]
                    foreign_percent, outstanding = self._foreign_ownership(ts_row, df.iloc[0])
                    if foreign_percent is not None:
                        df['foreignPercent'] = foreign_percent
                    df['outstandingShare'] = outstanding
            except Exception as e:
                logger.warning(f"Could not enrich trading_stats for {symbol}: {e}")

            # Enrich with shareholders() for shareholder count
            try:
                sh_df = await vnstock_call(stock.company.shareholders)
                if sh_df is not None and not sh_df.empty:
                    df['noShareholders'] = len(sh_df)
            except Exception as e:
                logger.warning(f"Could not enrich shareholders for {symbol}: {e}")

            # Convert NaN/NaT to None for JSON serialisation
            df = df.where(df.notna(), None)
            records = df.to_dict(orient='records')
            logger.info(f"Fetched company profile for {symbol}: {len(records)} records")
            return records

        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(f"vnstock rate limit hit fetching profile for {symbol} — retry later")
            else:
                logger.error(f"Error fetching company profile for {symbol}: {e}")
            return []

    @staticmethod
    def _flexible_rename(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
        """Version-resilient column renaming using partial matching.

        vnstock column names may change between versions (e.g. added units,
        rephrased labels).  This mapper tries exact match first, then falls
        back to substring matching so minor changes don't break the mapping.
        For multi-level columns (ratio), it flattens them first.
        """
        # Flatten multi-level columns (ratio returns tuples like ('Category', 'Metric'))
        if df.columns.nlevels > 1:
            df.columns = [col[-1] if isinstance(col, tuple) else col for col in df.columns]

        rename_map = {}
        used_targets = set()
        remaining_sources = dict(column_map)

        # Pass 1: exact match
        for src, tgt in list(remaining_sources.items()):
            if src in df.columns and tgt not in used_targets:
                rename_map[src] = tgt
                used_targets.add(tgt)
                del remaining_sources[src]

        # Pass 2: partial / substring match (case-insensitive)
        for src, tgt in list(remaining_sources.items()):
            if tgt in used_targets:
                continue
            src_lower = src.lower()
            for col in df.columns:
                col_str = str(col)
                if col_str in rename_map:
                    continue
                if src_lower in col_str.lower():
                    rename_map[col_str] = tgt
                    used_targets.add(tgt)
                    break

        if rename_map:
            df = df.rename(columns=rename_map)
        return df

    async def get_financial_statement(
        self, symbol: str, statement_type: str, period: str = "annual"
    ) -> List[dict]:
        """Get raw financial statement data from vnstock.

        Args:
            symbol: Stock ticker (e.g. FPT)
            statement_type: One of 'income_statement', 'cash_flow',
                            'balance_sheet', 'ratio'
            period: 'annual' or 'quarter'

        Returns:
            List of dicts, one per reporting period, with columns renamed
            to match the frontend field expectations.
        """
        try:
            source = FINANCIAL_SOURCE_OVERRIDES.get(
                statement_type, settings.VNSTOCK_DATA_SOURCE
            )
            stock = self.vnstock.stock(symbol=symbol.upper(), source=source)
            method = getattr(stock.finance, statement_type, None)
            if method is None:
                logger.error(f"Unknown statement type: {statement_type}")
                return []

            vnstock_period = VNSTOCK_PERIODS.get(str(period).lower())
            if vnstock_period is None:
                logger.error(
                    "Unknown period %r for %s %s — refusing to call vnstock, "
                    "which would silently return quarterly data. Valid: %s",
                    period, symbol, statement_type, sorted(VNSTOCK_PERIODS),
                )
                return []

            call_kwargs = {"period": vnstock_period}
            if SOURCE_SUPPORTS_LANG.get(source, True):
                call_kwargs["lang"] = "en"
            df = await vnstock_call(method, **call_kwargs)

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return []
            if isinstance(df, pd.Series):
                df = df.to_frame().T

            # A repeated column label is how this whole defect stayed
            # invisible: `to_dict(orient="records")` keeps exactly ONE value
            # per key, so duplicated labels discard data without raising.
            # Warn loudly and RENAME so the values survive, rather than
            # letting a future vendor reshape fail silently again.
            #
            # NOTE: deliberately NOT `_dedupe_columns`, which DROPS repeats.
            # That is right for `overview()`, where a repeated `issue_share`
            # is the same field four times — but here a repeated label is a
            # different REPORTING PERIOD, so dropping would be the data loss
            # this guard exists to prevent. Do not "tidy" these together.
            if isinstance(df, pd.DataFrame) and df.columns.duplicated().any():
                dups = sorted({str(c) for c in df.columns[df.columns.duplicated()]})
                logger.warning(
                    "%s %s/%s: duplicate column labels %s — vnstock's shape has "
                    "changed; de-duplicating so values are not silently dropped",
                    symbol, statement_type, period, dups,
                )
                seen: dict = {}
                renamed = []
                for c in df.columns:
                    key = str(c)
                    if key in seen:
                        seen[key] += 1
                        renamed.append(f"{key}__{seen[key]}")
                    else:
                        seen[key] = 0
                        renamed.append(key)
                df = df.copy()
                df.columns = renamed

            # Apply version-resilient column mapping
            col_map = self.FINANCIAL_STATEMENT_MAPS.get(statement_type, {})
            if col_map:
                df = self._flexible_rename(df, col_map)

            # Drop ticker column (redundant) and length_report if present
            for drop_col in ['ticker', 'lengthReport']:
                if drop_col in df.columns:
                    df = df.drop(columns=[drop_col])

            # Convert NaN to None for JSON
            df = df.where(df.notna(), None)
            records = df.to_dict(orient='records')
            logger.info(
                f"Fetched {statement_type} for {symbol}: {len(records)} rows, "
                f"columns: {list(df.columns[:8])}..."
            )
            return records

        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(f"vnstock rate limit hit fetching {statement_type} for {symbol} — retry later")
            else:
                logger.error(f"Error fetching {statement_type} for {symbol}: {e}")
            return []

    async def get_company_news_data(self, symbol: str) -> List[dict]:
        """Get company news from vnstock."""
        try:
            stock = self.vnstock.stock(symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE)
            df = await vnstock_call(stock.company.news)

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return []

            if isinstance(df, pd.Series):
                df = df.to_frame().T

            df = self._standardize_df(df, self.NEWS_COLUMN_MAP, convert_dates=True)

            # Calculate change = price - referencePrice
            if 'price' in df.columns and 'referencePrice' in df.columns:
                df['change'] = pd.to_numeric(df['price'], errors='coerce') - pd.to_numeric(df['referencePrice'], errors='coerce')

            df = df.where(df.notna(), None)
            records = df.to_dict(orient='records')
            logger.info(f"Fetched company news for {symbol}: {len(records)} records")
            return records

        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(f"vnstock rate limit hit fetching news for {symbol} — retry later")
            else:
                logger.error(f"Error fetching company news for {symbol}: {e}")
            return []

    async def get_company_events_data(self, symbol: str) -> List[dict]:
        """Get company events from vnstock."""
        try:
            stock = self.vnstock.stock(symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE)
            df = await vnstock_call(stock.company.events)

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return []

            if isinstance(df, pd.Series):
                df = df.to_frame().T

            df = self._standardize_df(df, self.EVENTS_COLUMN_MAP)
            df = df.where(df.notna(), None)
            records = df.to_dict(orient='records')
            logger.info(f"Fetched company events for {symbol}: {len(records)} records")
            return records

        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(f"vnstock rate limit hit fetching events for {symbol} — retry later")
            else:
                logger.error(f"Error fetching company events for {symbol}: {e}")
            return []

    async def get_company_dividends_data(self, symbol: str) -> List[dict]:
        """Get company dividends from vnstock."""
        try:
            stock = self.vnstock.stock(symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE)

            data_source = stock.company.data_source
            if not hasattr(data_source, 'dividends'):
                # VCI has no dividends(); fall back to its corporate events (#59)
                if hasattr(data_source, '_fetch_events'):
                    return await self._get_dividends_from_events(data_source, symbol)
                logger.info(f"Dividend data not supported by {settings.VNSTOCK_DATA_SOURCE} for {symbol}")
                return []

            df = await vnstock_call(stock.company.dividends)

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                logger.info(f"Dividend data not available for {symbol} - API limitation")
                return []

            if isinstance(df, pd.Series):
                df = df.to_frame().T

            df = df.where(df.notna(), None)
            records = df.to_dict(orient='records')
            logger.info(f"Fetched company dividends for {symbol}: {len(records)} records")
            return records

        except AttributeError:
            logger.info(f"Dividend data not supported for {symbol} - source limitation")
            return []
        except Exception as e:
            if _is_rate_limit(e):
                logger.warning(f"vnstock rate limit hit fetching dividends for {symbol} — retry later")
            else:
                logger.error(f"Error fetching company dividends for {symbol}: {e}")
            return []

    async def _get_dividends_from_events(self, data_source, symbol: str) -> List[dict]:
        """Page through VCI DIV/ISS corporate events and keep the distributions."""
        events: List[dict] = []
        for page in range(DIVIDEND_EVENTS_MAX_PAGES):
            batch = await vnstock_call(
                data_source._fetch_events,
                event_codes="DIV,ISS",
                from_date=DIVIDEND_EVENTS_FROM_DATE,
                page=page,
                size=DIVIDEND_EVENTS_PAGE_SIZE,
            )
            events.extend(batch or [])
            if not batch or len(batch) < DIVIDEND_EVENTS_PAGE_SIZE:
                break
        records = self._dividend_events_to_records(events)
        logger.info(f"Fetched company dividends for {symbol} from events: {len(records)} records")
        return records

    @staticmethod
    def _dividend_events_to_records(events: List[dict]) -> List[dict]:
        """Map raw VCI events to the dividend rows the frontend reads
        (title, exrightDate, issueDate, ratio, value, eventType/eventTypeEn).
        Newest ex-right date first; non-distribution share issues dropped."""
        def _day(value) -> Optional[str]:
            return str(value)[:10] if value else None

        records = []
        for ev in events:
            code = ev.get("eventCode")
            title_en = ev.get("eventTitleEn") or ""
            if code == "DIV":
                kind_vi, kind_en = "Tiền mặt", "Cash"
                paid = ev.get("payoutDate")
                value = ev.get("valuePerShare")
            elif code == "ISS":
                kind = next(
                    (k for k in DIVIDEND_SHARE_ISSUE_KINDS if k[0] in title_en.lower()),
                    None,
                )
                if kind is None:
                    continue
                _, kind_vi, kind_en = kind
                paid = ev.get("issueDate") or ev.get("listingDate")
                value = None
            else:
                continue
            records.append({
                "title": ev.get("eventTitleVi") or title_en or None,
                "titleEn": title_en or None,
                "eventCode": code,
                "eventType": kind_vi,
                "eventTypeEn": kind_en,
                "recordDate": _day(ev.get("recordDate")),
                "exrightDate": _day(ev.get("exrightDate")),
                "issueDate": _day(paid),
                "ratio": ev.get("exerciseRatio"),
                "value": value,
            })
        records.sort(key=lambda r: r["exrightDate"] or "", reverse=True)
        return records

    # ==================== Cached Company Data (DB-first) ====================

    async def get_company_profile_cached(self, symbol: str) -> List[dict]:
        """Return company profile from DB cache. Falls back to live vnstock for non-VN30."""
        profile = await self.repository.get_company_profile(symbol)
        if not profile:
            logger.info(f"{symbol} not in profile cache, falling back to live vnstock")
            return await self.get_company_profile_data(symbol)
        return [{
            "ticker": profile.ticker,
            "companyProfile": profile.company_profile,
            "history": profile.history,
            "industry": profile.industry,
            "industryL2": profile.industry_l2,
            "industryL3": profile.industry_l3,
            "charterCapital": profile.charter_capital,
            "issueShare": profile.issue_share,
            "outstandingShare": profile.outstanding_share,
            "foreignPercent": profile.foreign_percent,
            "freeFloatRate": profile.free_float_rate,
            "noShareholders": profile.no_shareholders,
            "noEmployees": profile.no_employees,
        }]

    async def get_financial_statement_cached(
        self, symbol: str, statement_type: str, period: str = "annual"
    ) -> List[dict]:
        """Return financial statement rows from DB cache. Falls back to live vnstock for non-VN30."""
        rows = await self.repository.get_financial_statements(symbol, statement_type, period)
        if not rows:
            logger.info(f"{symbol} {statement_type}/{period} not in cache, falling back to live vnstock")
            return await self.get_financial_statement(symbol, statement_type, period)
        results = []
        for row in rows:
            try:
                results.append(json.loads(row.data))
            except json.JSONDecodeError:
                logger.warning(f"Bad JSON in financial_statements id={row.id}")
        return results

    @classmethod
    def _foreign_ownership(cls, ts_row: pd.Series, overview_row: pd.Series):
        """(foreign_percent, outstanding_share) from a trading_stats() row.

        vnstock 3.x: current_holding_ratio + foreign_holding_room, from which
        outstanding shares = room / ratio. vnstock 4.x: foreigner_percentage
        and number_of_shares_mkt_cap / issue_share directly. Falls back to the
        overview's issueShare for outstanding shares.
        """
        first = cls._first_value
        ratio = first(ts_row, "current_holding_ratio", "foreigner_percentage")
        holding = first(ts_row, "foreign_holding_room")
        foreign_percent = float(ratio) if ratio is not None else None

        outstanding = None
        if ratio and float(ratio) > 0 and holding:
            outstanding = int(float(holding) / float(ratio))
        else:
            shares = first(ts_row, "number_of_shares_mkt_cap", "issue_share")
            if shares is None:
                shares = first(overview_row, "issueShare")
            if shares is not None:
                try:
                    outstanding = int(float(shares))
                except (ValueError, TypeError):
                    outstanding = None
        return foreign_percent, outstanding

    async def sync_company_profile(self, symbol: str) -> bool:
        """Fetch profile from vnstock and save to DB cache."""
        try:
            stock = self.vnstock.stock(symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE)
            df = await vnstock_call(stock.company.overview)

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                logger.warning(f"No overview data for {symbol}")
                return False

            if isinstance(df, pd.Series):
                df = df.to_frame().T

            df = self._dedupe_columns(df)
            df = self._dedupe_columns(self._standardize_df(df, self.OVERVIEW_COLUMN_MAP))
            row = df.iloc[0]
            first = self._first_value

            charter_capital = first(row, "charterCapital")
            issue_share = first(row, "issueShare")
            kwargs = {
                "company_profile": first(row, "companyProfile"),
                "history": first(row, "history"),
                "industry": first(row, "industry"),
                "industry_l2": first(row, "industryL2"),
                "industry_l3": first(row, "industryL3"),
                "charter_capital": float(charter_capital) if charter_capital is not None else None,
                "issue_share": float(issue_share) if issue_share is not None else None,
            }
            # vnstock 4.x carries foreign ownership on overview() itself
            if first(row, "foreignPercent") is not None:
                kwargs["foreign_percent"] = float(first(row, "foreignPercent"))

            # Enrich with trading_stats for foreign ownership
            try:
                ts_df = await vnstock_call(stock.company.trading_stats)
                if ts_df is not None and not ts_df.empty:
                    ts_row = self._dedupe_columns(ts_df).iloc[0]
                    foreign_percent, outstanding = self._foreign_ownership(ts_row, row)
                    if foreign_percent is not None:
                        kwargs["foreign_percent"] = foreign_percent
                    if outstanding is not None:
                        kwargs["outstanding_share"] = outstanding
            except Exception as e:
                logger.warning(f"Could not enrich trading_stats for {symbol}: {e}")

            # Enrich with shareholders count
            try:
                sh_df = await vnstock_call(stock.company.shareholders)
                if sh_df is not None and not sh_df.empty:
                    kwargs["no_shareholders"] = len(sh_df)
            except Exception as e:
                logger.warning(f"Could not enrich shareholders for {symbol}: {e}")

            # Get no_employees from overview if available (3.x only)
            if first(row, "noEmployees") is not None:
                try:
                    kwargs["no_employees"] = int(first(row, "noEmployees"))
                except (ValueError, TypeError):
                    pass

            # Get free_float_rate from overview if available
            if first(row, "freeFloatRate") is not None:
                try:
                    kwargs["free_float_rate"] = float(first(row, "freeFloatRate"))
                except (ValueError, TypeError):
                    pass

            await self.repository.upsert_company_profile(symbol.upper(), **kwargs)
            logger.info(f"Synced company profile for {symbol}")
            return True

        except Exception as e:
            logger.error(f"Error syncing company profile for {symbol}: {e}")
            try:
                await self.repository.session.rollback()
            except Exception:
                pass
            return False

    async def sync_company_financials(self, symbol: str) -> int:
        """Fetch all 4 financial statement types and save to DB cache."""
        total = 0
        for stmt_type in ["income_statement", "cash_flow", "balance_sheet", "ratio"]:
            for period in ["annual"]:
                try:
                    records = await self.get_financial_statement(symbol, stmt_type, period)
                    if not records:
                        continue
                    db_records = []
                    for rec in records:
                        report_year = rec.get("report_year") or rec.get("metayearreport")
                        try:
                            report_year = int(report_year) if report_year else None
                        except (ValueError, TypeError):
                            report_year = None
                        db_records.append({
                            "report_year": report_year,
                            "data": json.dumps(rec, default=str),
                        })
                    count = await self.repository.bulk_upsert_financial_statements(
                        symbol, stmt_type, period, db_records
                    )
                    total += count
                    logger.info(f"Synced {count} {stmt_type}/{period} rows for {symbol}")
                except Exception as e:
                    logger.error(f"Error syncing {stmt_type}/{period} for {symbol}: {e}")
                    try:
                        await self.repository.session.rollback()
                    except Exception:
                        pass
        return total

    async def is_company_data_stale(self) -> bool:
        """Check if company data needs re-sync (empty or older than configured days)."""
        count = await self.repository.count_company_profiles()
        # An interrupted sync leaves a partial cache; every missing VN30
        # symbol then costs 3 live vnstock calls per profile view.
        if count < len(self.STOCK_GROUPS["VN30"]):
            return True
        oldest = await self.repository.get_oldest_profile_sync()
        if oldest is None:
            return True
        from datetime import timedelta as td
        return (datetime.utcnow() - oldest) > td(days=settings.COMPANY_SYNC_STALE_DAYS)

    async def sync_all_company_data(self) -> dict:
        """Sync profiles, financials, and historical prices for all VN30 companies."""
        symbols = self.STOCK_GROUPS["VN30"]
        results = {"profiles": 0, "financials": 0, "historical": 0, "errors": []}
        vnstock_background.set(True)  # let interactive requests take quota slots first

        for symbol in symbols:
            try:
                # Sync profile
                ok = await self.sync_company_profile(symbol)
                if ok:
                    results["profiles"] += 1

                # Sync financials
                fin_count = await self.sync_company_financials(symbol)
                results["financials"] += fin_count

                # Sync historical price data (5 years)
                try:
                    sync_result = await self.ensure_company_and_sync(symbol)
                    results["historical"] += sync_result.get("synced", 0)
                    if sync_result.get("skipped"):
                        logger.info(f"Historical data for {symbol} already fresh, skipped")
                except Exception as hist_err:
                    logger.error(f"Error syncing historical data for {symbol}: {hist_err}")
                    results["errors"].append(f"{symbol}-historical: {hist_err}")
                    try:
                        await self.repository.session.rollback()
                    except Exception:
                        pass

                logger.info(f"Completed sync for {symbol}")
            except Exception as e:
                logger.error(f"Error syncing {symbol}: {e}")
                results["errors"].append(f"{symbol}: {e}")
                try:
                    await self.repository.session.rollback()
                except Exception:
                    pass

            # Rate limit: 2s between symbols
            await asyncio.sleep(2)

        logger.info(
            f"Company data sync complete: {results['profiles']} profiles, "
            f"{results['financials']} financial rows, "
            f"{results['historical']} historical records, "
            f"{len(results['errors'])} errors"
        )
        return results

    # ==================== Ensure Company & Sync ====================

    async def ensure_company_and_sync(self, symbol: str) -> dict:
        """
        Ensure a company record exists in DB and sync historical price data.
        Used when a user adds a stock to their portfolio.

        Returns dict with status info: {"created": bool, "synced": int, "skipped": bool}
        """
        symbol = symbol.upper()
        company = await self.repository.get_company_by_symbol(symbol)

        if company and company.last_synced_at:
            # Skip if synced within the last 24 hours
            hours_since_sync = (datetime.utcnow() - company.last_synced_at).total_seconds() / 3600
            if hours_since_sync < 24:
                logger.info(f"Skipping sync for {symbol}, last synced {hours_since_sync:.1f}h ago")
                return {"created": False, "synced": 0, "skipped": True}

        created = False
        if not company:
            # Fetch company info from vnstock and create record
            logger.info(f"Company {symbol} not found in DB, creating from vnstock")
            try:
                stock = self.vnstock.stock(symbol=symbol, source=settings.VNSTOCK_DATA_SOURCE)
                all_symbols_df = stock.listing.all_symbols()

                company_name = symbol
                exchange = "HOSE"
                if all_symbols_df is not None and not all_symbols_df.empty:
                    match = all_symbols_df[all_symbols_df["symbol"] == symbol]
                    if not match.empty:
                        company_name = match.iloc[0].get("organ_name", match.iloc[0].get("organName", symbol))
                        exchange = match.iloc[0].get("exchange", "HOSE") or "HOSE"

                company = await self.repository.create_company(
                    symbol=symbol,
                    name=company_name,
                    exchange=exchange,
                )
                created = True
                logger.info(f"Created company record for {symbol}: {company_name}")
            except Exception as e:
                logger.error(f"Failed to create company record for {symbol}: {e}")
                raise

        # Backlog #87: depth comes from config, not from a literal. The vendor
        # carries ~17 years; 5 was the monolith's DEFAULT_YEARS_HISTORY and the
        # reason EM-4 could not test E&M's bottoms claim.
        end_date = date.today()
        start_date = end_date - timedelta(days=365 * settings.HISTORY_YEARS)

        try:
            count = await self.fetch_and_save_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            logger.info(f"Synced {count} historical records for {symbol}")
            return {"created": created, "synced": count, "skipped": False}
        except Exception as e:
            logger.error(f"Failed to sync historical data for {symbol}: {e}")
            raise

    # ==================== Historical Data Operations ====================

    async def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[HistoricalDataResponse]:
        """Get historical price data for a symbol"""
        # Default to last 1 year
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        company = await self.repository.get_company_by_symbol(symbol)

        if company:
            # Try to get from database first
            prices = await self.repository.get_historical_prices(
                company_id=company.id,
                start_date=start_date,
                end_date=end_date,
            )

            if prices:
                # Sort by date ascending
                prices.sort(key=lambda x: x.date)

                price_responses = [
                    StockPriceResponse(
                        date=p.date,
                        open=p.open,
                        high=p.high,
                        low=p.low,
                        close=p.close,
                        volume=p.volume,
                        value=p.value,
                        adj_close=p.adj_close,
                        change=p.change,
                        change_percent=p.change_percent,
                    )
                    for p in prices
                ]

                return HistoricalDataResponse(
                    symbol=company.symbol,
                    name=company.name,
                    exchange=company.exchange,
                    data=price_responses,
                    count=len(price_responses),
                )

        # Fallback: Fetch live data directly from vnstock
        logger.info(f"Database empty for {symbol}, fetching live historical data from vnstock")
        return await self._get_historical_data_live(symbol, start_date, end_date)

    async def _get_historical_data_live(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> Optional[HistoricalDataResponse]:
        """
        Fetch historical data directly from vnstock API.
        Used as fallback when database is empty.
        """
        try:
            stock = self.vnstock.stock(symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE)
            df = await vnstock_call(
                stock.quote.history,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
            )

            if df is None or df.empty:
                logger.warning(f"No historical data returned from vnstock for {symbol}")
                return None

            # Get company name from listing data
            company_name = symbol.upper()
            try:
                all_symbols_df = await vnstock_call(stock.listing.all_symbols)
                if all_symbols_df is not None and not all_symbols_df.empty:
                    match = all_symbols_df[all_symbols_df["symbol"] == symbol.upper()]
                    if not match.empty:
                        company_name = match.iloc[0].get("organ_name", match.iloc[0].get("organName", symbol.upper()))
            except Exception as e:
                logger.warning(f"Could not fetch company name for {symbol}: {e}")

            # Convert DataFrame to StockPriceResponse list
            price_responses = []
            for _, row in df.iterrows():
                # Handle different date column names
                row_date = row.get("time", row.name)
                if hasattr(row_date, "date"):
                    row_date = row_date.date()
                elif isinstance(row_date, str):
                    row_date = datetime.strptime(row_date, "%Y-%m-%d").date()

                price_responses.append(
                    StockPriceResponse(
                        date=row_date,
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=int(row.get("volume", 0)),
                        value=None,
                        adj_close=adjusted_close(row),
                        change=None,
                        change_percent=None,
                    )
                )

            # Sort by date ascending
            price_responses.sort(key=lambda x: x.date)

            logger.info(f"Fetched {len(price_responses)} historical records from vnstock for {symbol}")

            return HistoricalDataResponse(
                symbol=symbol.upper(),
                name=company_name,
                exchange=None,
                data=price_responses,
                count=len(price_responses),
            )

        except Exception as e:
            logger.error(f"Error fetching historical data from vnstock for {symbol}: {e}")
            return None

    async def fetch_and_save_historical_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """Fetch historical data from VNStock and save to database"""
        company = await self.repository.get_company_by_symbol(symbol)
        if not company:
            raise ValueError(f"Company not found: {symbol}")

        # Default dates
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        try:
            # Fetch from VNStock (run in thread to avoid blocking event loop)
            stock = self.vnstock.stock(symbol=symbol, source=settings.VNSTOCK_DATA_SOURCE)
            df = await vnstock_call(
                stock.quote.history,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
            )

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return 0

            # Convert to StockPrice objects
            prices = []
            for _, row in df.iterrows():
                price = StockPrice(
                    company_id=company.id,
                    date=row.get("time", row.name).date() if hasattr(row.get("time", row.name), "date") else row.get("time", row.name),
                    open=row.get("open"),
                    high=row.get("high"),
                    low=row.get("low"),
                    close=row.get("close"),
                    adj_close=adjusted_close(row),
                    volume=int(row.get("volume", 0)),
                )
                prices.append(price)

            # Save to database
            count = await self.repository.save_prices(prices)

            # Update company sync timestamp
            await self.repository.update_company(
                company.id,
                last_synced_at=datetime.utcnow()
            )

            return count

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            raise

    # ==================== Top Movers ====================

    async def get_top_gainers(self, limit: int = 10) -> List[TopMoverResponse]:
        """Get top gaining stocks"""
        results = await self.repository.get_top_gainers(limit)

        # If database is empty, fallback to live data
        if not results:
            logger.info("Database empty, fetching live top gainers from price board")
            return await self._get_top_movers_live(limit=limit, sort_by="gainers")

        return [
            TopMoverResponse(
                symbol=company.symbol,
                name=company.name,
                exchange=company.exchange,
                close=price.close,
                change=price.change or 0,
                change_percent=price.change_percent or 0,
                volume=price.volume or 0,
            )
            for company, price in results
        ]

    async def get_top_losers(self, limit: int = 10) -> List[TopMoverResponse]:
        """Get top losing stocks"""
        results = await self.repository.get_top_losers(limit)

        # If database is empty, fallback to live data
        if not results:
            logger.info("Database empty, fetching live top losers from price board")
            return await self._get_top_movers_live(limit=limit, sort_by="losers")

        return [
            TopMoverResponse(
                symbol=company.symbol,
                name=company.name,
                exchange=company.exchange,
                close=price.close,
                change=price.change or 0,
                change_percent=price.change_percent or 0,
                volume=price.volume or 0,
            )
            for company, price in results
        ]

    async def get_most_active(self, limit: int = 10) -> List[TopMoverResponse]:
        """Get most active stocks by volume"""
        results = await self.repository.get_top_volume(limit)

        # If database is empty, fallback to live data
        if not results:
            logger.info("Database empty, fetching live most active from price board")
            return await self._get_top_movers_live(limit=limit, sort_by="volume")

        return [
            TopMoverResponse(
                symbol=company.symbol,
                name=company.name,
                exchange=company.exchange,
                close=price.close,
                change=price.change or 0,
                change_percent=price.change_percent or 0,
                volume=price.volume or 0,
            )
            for company, price in results
        ]

    async def _get_top_movers_live(self, limit: int = 10, sort_by: str = "gainers") -> List[TopMoverResponse]:
        """
        Get top movers from live price board data.

        Args:
            limit: Number of results to return
            sort_by: "gainers" for top gainers, "losers" for top losers, "volume" for most active
        """
        try:
            # Fetch price board for VN100 to get a broader market view
            price_data = await self.get_price_board(group="VN100")

            if not price_data:
                # Fallback to VN30 if VN100 fails
                price_data = await self.get_price_board(group="VN30")

            if not price_data:
                logger.warning("No price board data available")
                return []

            # Get company names for enrichment
            company_names = {}
            try:
                stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)
                all_symbols_df = stock.listing.all_symbols()
                if all_symbols_df is not None and not all_symbols_df.empty:
                    for _, row in all_symbols_df.iterrows():
                        symbol = row.get("symbol", "")
                        name = row.get("organ_name", row.get("organName", ""))
                        if symbol and name:
                            company_names[symbol] = name
            except Exception as e:
                logger.warning(f"Could not load company names: {e}")

            # Filter out entries without valid price data
            valid_data = [
                item for item in price_data
                if item.get("matchPrice") and item.get("changePercent") is not None
            ]

            # Sort based on criteria
            if sort_by == "gainers":
                # Sort by change percent descending, filter positive changes
                sorted_data = sorted(
                    [d for d in valid_data if (d.get("changePercent") or 0) > 0],
                    key=lambda x: x.get("changePercent", 0),
                    reverse=True
                )
            elif sort_by == "losers":
                # Sort by change percent ascending, filter negative changes
                sorted_data = sorted(
                    [d for d in valid_data if (d.get("changePercent") or 0) < 0],
                    key=lambda x: x.get("changePercent", 0),
                    reverse=False
                )
            else:  # volume
                # Sort by total volume descending
                sorted_data = sorted(
                    valid_data,
                    key=lambda x: x.get("totalQty", 0) or 0,
                    reverse=True
                )

            # Take top N results
            top_results = sorted_data[:limit]

            # Convert to TopMoverResponse
            movers = []
            for item in top_results:
                symbol = item.get("symbol", "")
                movers.append(TopMoverResponse(
                    symbol=symbol,
                    name=company_names.get(symbol, symbol),
                    exchange=item.get("exchange", "HOSE"),
                    close=item.get("matchPrice", 0),
                    change=item.get("change", 0) or 0,
                    change_percent=item.get("changePercent", 0) or 0,
                    volume=item.get("totalQty", 0) or 0,
                ))

            logger.info(f"Fetched {len(movers)} {sort_by} from live price board")
            return movers

        except Exception as e:
            logger.error(f"Error fetching top movers from live data: {e}")
            return []

    # ==================== Industry Operations ====================

    async def get_all_industries(self) -> List[IndustryResponse]:
        """Get all industries"""
        industries = await self.repository.get_all_industries()

        # If database is empty, fallback to live data from vnstock
        if not industries:
            logger.info("Database empty, fetching live industry data from vnstock")
            return await self.get_all_industries_live()

        return [
            IndustryResponse(
                id=i.id,
                code=i.code,
                name=i.name,
                name_en=i.name_en,
                description=i.description,
                level=i.level,
            )
            for i in industries
        ]

    async def get_all_industries_live(self) -> List[IndustryResponse]:
        """
        Get all industries from vnstock (live data).
        Uses symbols_by_industries() to extract unique industries since
        industries_icb() is not available for all data sources.
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)

            # Try industries_icb() first, fallback to symbols_by_industries()
            try:
                df = stock.listing.industries_icb()
                if df is not None and not df.empty:
                    industries = []
                    for idx, row in df.iterrows():
                        industry = IndustryResponse(
                            id=idx + 1,
                            code=str(row.get("icb_code", row.get("icbCode", ""))),
                            name=row.get("icb_name", row.get("icbName", "")),
                            name_en=row.get("en_icb_name", row.get("enIcbName", None)),
                            description=None,
                            level=int(row.get("level", 1)) if row.get("level") is not None else 1,
                        )
                        industries.append(industry)
                    logger.info(f"Fetched {len(industries)} industries from industries_icb()")
                    return industries
            except Exception as icb_error:
                logger.warning(f"industries_icb() not available: {icb_error}, trying symbols_by_industries()")

            # Fallback: Use symbols_by_industries() and extract unique industries
            df = stock.listing.symbols_by_industries()

            if df is None or df.empty:
                logger.warning("No data returned from vnstock symbols_by_industries")
                return []

            # Log columns for debugging
            logger.info(f"symbols_by_industries columns: {df.columns.tolist()}")

            # Extract unique industries from the data
            # Look for icb_code2/icb_name2 (level 2 industries) as they are broader categories
            industries = []
            seen_codes = set()

            # Determine which columns to use for industry extraction
            code_col = None
            name_col = None
            name_en_col = None

            for col in ['industry_code', 'icb_code2', 'icb_code3', 'icb_code']:
                if col in df.columns:
                    code_col = col
                    break

            for col in ['industry_name', 'icb_name2', 'icb_name3', 'icb_name']:
                if col in df.columns:
                    name_col = col
                    break

            for col in ['industry_name_en', 'en_icb_name2', 'en_icb_name3', 'en_icb_name']:
                if col in df.columns:
                    name_en_col = col
                    break

            if code_col is None or name_col is None:
                logger.warning(f"Could not find industry columns. Available: {df.columns.tolist()}")
                return []

            idx = 1
            for _, row in df.iterrows():
                code = str(row.get(code_col, ""))
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    industry = IndustryResponse(
                        id=idx,
                        code=code,
                        name=row.get(name_col, ""),
                        name_en=row.get(name_en_col, None) if name_en_col else None,
                        description=None,
                        level=2 if 'icb_code2' in code_col else 3,
                    )
                    industries.append(industry)
                    idx += 1

            # Sort by code
            industries.sort(key=lambda x: x.code)

            logger.info(f"Extracted {len(industries)} unique industries from symbols_by_industries()")
            return industries

        except Exception as e:
            logger.error(f"Error fetching industries from vnstock: {e}")
            return []

    async def get_companies_by_industry(
        self,
        industry_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> List[CompanyResponse]:
        """Get companies in an industry"""
        skip = (page - 1) * page_size
        companies = await self.repository.get_companies_by_industry(
            industry_id=industry_id,
            skip=skip,
            limit=page_size,
        )

        return [
            CompanyResponse(
                id=c.id,
                symbol=c.symbol,
                name=c.name,
                name_en=c.name_en,
                exchange=c.exchange,
                industry_id=c.industry_id,
                listing_date=c.listing_date,
                outstanding_shares=c.outstanding_shares,
                market_cap=c.market_cap,
                website=c.website,
                description=c.description,
                is_active=c.is_active,
                is_tradeable=c.is_tradeable,
            )
            for c in companies
        ]

    async def get_companies_by_industry_code(
        self,
        industry_code: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[CompanyResponse]:
        """
        Get companies in an industry by ICB code.
        Falls back to vnstock live data when database is empty.
        """
        # First try to get from database
        skip = (page - 1) * page_size

        # Try to find industry by code in database
        industry = await self.repository.get_industry_by_code(industry_code)

        if industry:
            companies = await self.repository.get_companies_by_industry(
                industry_id=industry.id,
                skip=skip,
                limit=page_size,
            )
            total = len(companies)  # This is simplified, ideally get count from repo
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            items = [
                CompanyResponse(
                    id=c.id,
                    symbol=c.symbol,
                    name=c.name,
                    name_en=c.name_en,
                    exchange=c.exchange,
                    industry_id=c.industry_id,
                    listing_date=c.listing_date,
                    outstanding_shares=c.outstanding_shares,
                    market_cap=c.market_cap,
                    website=c.website,
                    description=c.description,
                    is_active=c.is_active,
                    is_tradeable=c.is_tradeable,
                )
                for c in companies
            ]

            return PaginatedResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        # Fallback to live data from vnstock
        logger.info(f"Database empty for industry {industry_code}, fetching live data from vnstock")
        return await self.get_companies_by_industry_code_live(
            industry_code=industry_code,
            page=page,
            page_size=page_size,
        )

    async def get_companies_by_industry_code_live(
        self,
        industry_code: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[CompanyResponse]:
        """
        Get companies by industry code from vnstock (live data).
        Uses symbols_by_industries() method and enriches with company names from all_symbols().
        """
        try:
            stock = self.vnstock.stock(symbol="VNM", source=settings.VNSTOCK_DATA_SOURCE)
            df = stock.listing.symbols_by_industries()

            if df is None or df.empty:
                logger.warning("No data returned from vnstock symbols_by_industries")
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                )

            # Log columns for debugging
            logger.info(f"get_companies_by_industry_code_live columns: {df.columns.tolist()}")

            # Filter by industry code - check various possible column names
            icb_col = None
            for col in ['industry_code', 'icb_code', 'icbCode', 'icb_code3', 'icb_code2', 'icb_code4']:
                if col in df.columns:
                    icb_col = col
                    break

            if icb_col is None:
                logger.warning(f"Could not find ICB code column in dataframe. Columns: {df.columns.tolist()}")
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                )

            # Filter by industry code (match start of code for hierarchical matching)
            filtered_df = df[df[icb_col].astype(str).str.startswith(str(industry_code))]

            if filtered_df.empty:
                logger.warning(f"No companies found for industry code: {industry_code}")
                return PaginatedResponse(
                    items=[],
                    total=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                )

            total = len(filtered_df)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0

            # Paginate
            skip = (page - 1) * page_size
            paginated_df = filtered_df.iloc[skip:skip + page_size]

            # Try to get company names from all_symbols() for enrichment
            company_names = {}
            try:
                all_symbols_df = stock.listing.all_symbols()
                if all_symbols_df is not None and not all_symbols_df.empty:
                    for _, sym_row in all_symbols_df.iterrows():
                        symbol = sym_row.get("symbol", "")
                        name = sym_row.get("organ_name", sym_row.get("organName", ""))
                        if symbol and name:
                            company_names[symbol] = name
                    logger.info(f"Loaded {len(company_names)} company names for enrichment")
            except Exception as e:
                logger.warning(f"Could not load company names for enrichment: {e}")

            # Determine column names for industry data
            name_col = None
            for col in ['industry_name', 'icb_name', 'icb_name2', 'icb_name3']:
                if col in df.columns:
                    name_col = col
                    break

            companies = []
            for idx, row in paginated_df.iterrows():
                symbol = row.get("symbol", row.get("ticker", ""))

                # Get industry name from the available column
                industry_name = row.get(name_col, "") if name_col else ""

                # Get industry code value
                ind_code = str(row.get(icb_col, "")) if icb_col else ""

                # Get company name from enrichment data or use symbol
                company_name = company_names.get(symbol, symbol)

                company = CompanyResponse(
                    id=0,
                    symbol=symbol,
                    name=company_name,
                    name_en=None,
                    exchange=row.get("exchange", None),
                    industry_id=None,
                    industry_name=industry_name,
                    icb_name2=industry_name,  # Use same industry name for display
                    icb_name3=ind_code,  # Show industry code in level 3
                    icb_name4=None,
                    com_type_code=row.get("com_type_code", None),
                    listing_date=None,
                    outstanding_shares=None,
                    market_cap=None,
                    website=None,
                    description=None,
                    is_active=True,
                    is_tradeable=True,
                )
                companies.append(company)

            logger.info(f"Fetched {len(companies)} companies for industry {industry_code} from vnstock")

            return PaginatedResponse(
                items=companies,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

        except Exception as e:
            logger.error(f"Error fetching companies by industry from vnstock: {e}")
            return PaginatedResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )

    # ==================== Market Index Operations ====================

    async def get_market_indices(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[MarketIndexResponse]:
        """Get market index data"""
        indices = await self.repository.get_market_indices(start_date, end_date)

        return [
            MarketIndexResponse(
                code=i.code,
                name=i.name,
                date=i.date,
                open=i.open,
                high=i.high,
                low=i.low,
                close=i.close,
                volume=i.volume,
                value=i.value,
                change=i.change,
                change_percent=i.change_percent,
            )
            for i in indices
        ]

    async def get_latest_indices(self) -> List[MarketIndexResponse]:
        """Get latest market index values"""
        indices = await self.repository.get_latest_indices()

        return [
            MarketIndexResponse(
                code=i.code,
                name=i.name,
                date=i.date,
                open=i.open,
                high=i.high,
                low=i.low,
                close=i.close,
                volume=i.volume,
                value=i.value,
                change=i.change,
                change_percent=i.change_percent,
            )
            for i in indices
        ]

    # ==================== Price Board Operations ====================

    # Stock group symbol mappings
    STOCK_GROUPS = {
        "VN30": ["ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
                 "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
                 "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"],
        "VN100": ["ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
                  "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
                  "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
                  "AGG", "ANV", "ASM", "BWE", "CII", "CMG", "DBC", "DCM", "DGC", "DGW",
                  "DIG", "DPM", "DXG", "ELC", "EVF", "FRT", "GEX", "HAG", "HCM", "HDC",
                  "HDG", "HHV", "HSG", "HT1", "IDC", "KBC", "KDC", "KDH", "LPB", "MIG",
                  "MSH", "NLG", "NT2", "NVL", "OCB", "PAN", "PC1", "PDR", "PHR", "PNJ",
                  "PPC", "PTB", "PVD", "PVS", "PVT", "REE", "SBT", "SCS", "SIP", "SJS",
                  "SZC", "TCH", "TLG", "TNH", "VCI", "VGC", "VHC", "VIX", "VND", "VOS",
                  "VPI", "VTP"],
    }

    # Browser-like headers for Vietcap API
    VIETCAP_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Origin': 'https://trading.vietcap.com.vn',
        'Referer': 'https://trading.vietcap.com.vn/'
    }

    async def get_price_board(self, group: str = "VN30") -> List[dict]:
        """
        Get price board data from DB cache.
        Refreshes live (fetch + store) if the group is empty or stale (#48):
        the nightly refresh runs at 01:00, so without this the board showed
        the previous session all day.
        """
        from sqlalchemy import select

        group_upper = group.upper()
        session = self.repository.session

        async with _get_price_board_lock(group_upper):
            result = await session.execute(
                select(PriceBoard).where(PriceBoard.stock_group == group_upper)
            )
            rows = result.scalars().all()

            if rows:
                stamps = [r.updated_at for r in rows]
                oldest = None if None in stamps else min(stamps)
                max_age = timedelta(seconds=settings.PRICE_BOARD_MAX_AGE_SECONDS)
                if not price_board_is_stale(oldest, _utcnow(), max_age):
                    logger.debug(f"Price board DB hit for {group_upper}: {len(rows)} rows")
                    return [self._price_board_row_to_dict(r) for r in rows]
                logger.info(f"Price board for {group_upper} is stale (oldest {oldest}), refreshing")
            else:
                logger.info(f"Price board DB empty for {group_upper}, fetching live data")

            count = await self.refresh_price_board(group_upper)
            if count == 0:
                # Keep serving what we have rather than blanking the board
                if rows:
                    logger.warning(f"Price board refresh failed for {group_upper}; serving stale rows")
                return [self._price_board_row_to_dict(r) for r in rows]

            result = await session.execute(
                select(PriceBoard).where(PriceBoard.stock_group == group_upper)
            )
            rows = result.scalars().all()
            return [self._price_board_row_to_dict(r) for r in rows]

    async def refresh_price_board(self, group: str = "VN30") -> int:
        """
        Fetch live data from Vietcap API, delete old rows, insert fresh ones.
        Returns count of inserted records.
        """
        from sqlalchemy import delete as sa_delete

        group_upper = group.upper()
        logger.info(f"Refreshing price board for {group_upper}")

        records = await self._fetch_price_board_live(group_upper)
        if not records:
            logger.warning(f"No live data returned for {group_upper}")
            return 0

        session = self.repository.session

        # Delete old rows for this group
        await session.execute(
            sa_delete(PriceBoard).where(PriceBoard.stock_group == group_upper)
        )

        # Insert fresh rows
        for rec in records:
            row = PriceBoard(
                symbol=rec["symbol"],
                stock_group=group_upper,
                ref_price=rec.get("refPrice"),
                ceiling=rec.get("ceiling"),
                floor=rec.get("floor"),
                match_price=rec.get("matchPrice"),
                match_qty=rec.get("matchQty"),
                match_value=rec.get("matchValue"),
                change=rec.get("change"),
                change_percent=rec.get("changePercent"),
                total_qty=rec.get("totalQty"),
                total_value=rec.get("totalValue"),
                highest=rec.get("highest"),
                lowest=rec.get("lowest"),
                open_price=rec.get("openPrice"),
                average_price=rec.get("averagePrice"),
                buy_price_1=rec.get("buyPrice1"),
                buy_qty_1=rec.get("buyQty1"),
                buy_price_2=rec.get("buyPrice2"),
                buy_qty_2=rec.get("buyQty2"),
                buy_price_3=rec.get("buyPrice3"),
                buy_qty_3=rec.get("buyQty3"),
                sell_price_1=rec.get("sellPrice1"),
                sell_qty_1=rec.get("sellQty1"),
                sell_price_2=rec.get("sellPrice2"),
                sell_qty_2=rec.get("sellQty2"),
                sell_price_3=rec.get("sellPrice3"),
                sell_qty_3=rec.get("sellQty3"),
                exchange=rec.get("exchange"),
                trading_status=rec.get("tradingStatus"),
            )
            session.add(row)

        await session.commit()
        logger.info(f"Refreshed price board for {group_upper}: {len(records)} records")

        # Fan out price updates so portfolio-service alerts (and others)
        # can react. Best-effort — does not block or fail the refresh.
        try:
            from app.services.event_publisher import publish_price_updates
            await publish_price_updates(records)
        except Exception as e:
            logger.error(f"Failed to publish price updates: {e}")

        return len(records)

    async def _fetch_price_board_live(self, group: str = "VN30") -> List[dict]:
        """Fetch live price board data from Vietcap API. Returns list of camelCase dicts.
        Uses requests (sync) via asyncio.to_thread — more reliable from Docker than httpx async.
        """
        import requests as sync_requests

        def _sync_fetch():
            symbols = self.STOCK_GROUPS.get(group.upper(), self.STOCK_GROUPS.get("VN30"))
            url = "https://trading.vietcap.com.vn/api/price/symbols/getList"
            response = sync_requests.post(
                url,
                json={"symbols": symbols},
                headers=self.VIETCAP_HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await asyncio.to_thread(_sync_fetch)
            if not data:
                return []

            records = []
            for item in data:
                listing = item.get("listingInfo", {})
                match_price = item.get("matchPrice", {})
                bid_ask = item.get("bidAsk", {})

                bid_prices = bid_ask.get("bidPrices", [])
                ask_prices = bid_ask.get("askPrices", [])

                current_price = match_price.get("matchPrice")
                ref_price = listing.get("refPrice")
                change = None
                change_percent = None
                if current_price and ref_price and ref_price > 0:
                    change = current_price - ref_price
                    change_percent = round((change / ref_price) * 100, 2)

                record = {
                    "symbol": listing.get("symbol"),
                    "refPrice": ref_price,
                    "ceiling": listing.get("ceiling"),
                    "floor": listing.get("floor"),
                    "matchPrice": current_price,
                    "matchQty": match_price.get("matchVol"),
                    "matchValue": match_price.get("accumulatedValue"),
                    "change": change,
                    "changePercent": change_percent,
                    "totalQty": match_price.get("accumulatedVolume"),
                    "totalValue": match_price.get("accumulatedValue"),
                    "highest": match_price.get("highest"),
                    "lowest": match_price.get("lowest"),
                    "openPrice": match_price.get("openPrice"),
                    "averagePrice": match_price.get("avgMatchPrice"),
                    "buyPrice1": bid_prices[0].get("price") if len(bid_prices) > 0 else None,
                    "buyQty1": bid_prices[0].get("volume") if len(bid_prices) > 0 else None,
                    "buyPrice2": bid_prices[1].get("price") if len(bid_prices) > 1 else None,
                    "buyQty2": bid_prices[1].get("volume") if len(bid_prices) > 1 else None,
                    "buyPrice3": bid_prices[2].get("price") if len(bid_prices) > 2 else None,
                    "buyQty3": bid_prices[2].get("volume") if len(bid_prices) > 2 else None,
                    "sellPrice1": ask_prices[0].get("price") if len(ask_prices) > 0 else None,
                    "sellQty1": ask_prices[0].get("volume") if len(ask_prices) > 0 else None,
                    "sellPrice2": ask_prices[1].get("price") if len(ask_prices) > 1 else None,
                    "sellQty2": ask_prices[1].get("volume") if len(ask_prices) > 1 else None,
                    "sellPrice3": ask_prices[2].get("price") if len(ask_prices) > 2 else None,
                    "sellQty3": ask_prices[2].get("volume") if len(ask_prices) > 2 else None,
                    "exchange": listing.get("board"),
                    "tradingStatus": listing.get("tradingStatus"),
                }
                records.append(record)

            logger.info(f"Fetched live price board for {len(records)} symbols in group {group}")
            return records

        except Exception as e:
            logger.error(f"Error fetching live price board for group {group}: {type(e).__name__}: {e}")
            return []

    @staticmethod
    def _price_board_row_to_dict(row: PriceBoard) -> dict:
        """Convert a PriceBoard DB row to the camelCase dict the frontend expects."""
        return {
            "symbol": row.symbol,
            "refPrice": row.ref_price,
            "ceiling": row.ceiling,
            "floor": row.floor,
            "matchPrice": row.match_price,
            "matchQty": row.match_qty,
            "matchValue": row.match_value,
            "change": row.change,
            "changePercent": row.change_percent,
            "totalQty": row.total_qty,
            "totalValue": row.total_value,
            "highest": row.highest,
            "lowest": row.lowest,
            "openPrice": row.open_price,
            "averagePrice": row.average_price,
            "buyPrice1": row.buy_price_1,
            "buyQty1": row.buy_qty_1,
            "buyPrice2": row.buy_price_2,
            "buyQty2": row.buy_qty_2,
            "buyPrice3": row.buy_price_3,
            "buyQty3": row.buy_qty_3,
            "sellPrice1": row.sell_price_1,
            "sellQty1": row.sell_qty_1,
            "sellPrice2": row.sell_price_2,
            "sellQty2": row.sell_qty_2,
            "sellPrice3": row.sell_price_3,
            "sellQty3": row.sell_qty_3,
            "exchange": row.exchange,
            "tradingStatus": row.trading_status,
        }

    # ==================== Financial Data Operations ====================

    async def _latest_close(self, symbol: str) -> Optional[float]:
        """Most recent daily close, in VND, or `None`.

        Backlog #97. Used to state market cap currently rather than at fiscal
        year end. Returns `None` rather than raising, because market cap is one
        field and a quote outage must not take the rest of the response with
        it.

        The vendor quotes in thousands of VND (FPT closes around 57.0), while
        BVPS is in VND (25,679.55), so the close is scaled by 1,000 to put
        both on one unit. Asserted by a test, because a silent 1000x error
        here would be invisible in a ratio and enormous in a market cap.
        """
        from datetime import timedelta as _td

        try:
            stock = self.vnstock.stock(
                symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE
            )
            end = date.today()
            df = await vnstock_call(
                stock.quote.history,
                start=(end - _td(days=21)).strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
            )
            if df is None or len(df) == 0 or "close" not in df.columns:
                return None
            close = float(df["close"].iloc[-1])
            return close * 1000.0 if close > 0 else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("latest close for %s unavailable: %s", symbol, exc)
            return None

    async def get_company_financials(self, symbol: str) -> Optional[CompanyFinancialsResponse]:
        """
        Get financial ratios and metrics for a company from vnstock.

        Args:
            symbol: Stock symbol (e.g., TCB, VNM)

        Returns:
            CompanyFinancialsResponse with financial ratios and metrics
        """
        try:
            stock = self.vnstock.stock(symbol=symbol.upper(), source=settings.VNSTOCK_DATA_SOURCE)

            # Get company name
            company_name = symbol.upper()
            try:
                all_symbols_df = stock.listing.all_symbols()
                if all_symbols_df is not None and not all_symbols_df.empty:
                    match = all_symbols_df[all_symbols_df["symbol"] == symbol.upper()]
                    if not match.empty:
                        company_name = match.iloc[0].get("organ_name", match.iloc[0].get("organName", symbol.upper()))
            except Exception as e:
                logger.warning(f"Could not fetch company name for {symbol}: {e}")

            # Initialize response with defaults
            financials = CompanyFinancialsResponse(
                symbol=symbol.upper(),
                company_name=company_name,
            )

            # Initialize nested structures
            financial_ratios = FinancialRatiosData()
            growth_metrics = GrowthMetricsData()
            income_statement = IncomeStatementData()
            balance_sheet = BalanceSheetData()
            cash_flow = CashFlowData()

            # Try to get financial ratios from vnstock
            try:
                ratio_df = stock.finance.ratio(period="quarter", lang="en")
                latest = self._latest_metrics(ratio_df)

                if latest:
                    # Extract ratios by metric name (long-format item_en values)
                    pe = self._pick(latest, 'P/E')
                    pb = self._pick(latest, 'P/B')
                    ps = self._pick(latest, 'P/S')
                    roe = self._as_percent(self._pick(latest, 'ROE (%)'))
                    roa = self._as_percent(self._pick(latest, 'ROA (%)'))
                    de = self._pick(latest, 'Debt to Equity')
                    cr = self._pick(latest, 'Current Ratio')
                    qr = self._pick(latest, 'Quick Ratio')
                    gm = self._as_percent(self._pick(latest, 'Gross Margin (%)'))
                    om = self._as_percent(self._pick(latest, 'EBIT Margin (%)'))
                    npm = self._as_percent(self._pick(latest, 'After-tax Profit Margin (%)'))
                    ev_ebitda = self._pick(latest, 'EV/EBITDA')
                    div_yield = self._as_percent(self._pick(latest, 'Dividend Yield (%)'))
                    # Backlog #97: `Market Cap` from this frame was ~3x stale
                    # (26.57T for FPT against roughly 84T today). KBS's ratio
                    # sheet carries no market cap, so it is RECOMPUTED from
                    # the balance sheet further down as `P/B x book equity` —
                    # algebraically exact, since P/B is market cap over book
                    # equity by definition, and it keeps market cap on the
                    # same fiscal-year basis as every other price-based ratio
                    # (reported by `ratios_as_of`). The stale vendor figure is
                    # never used.
                    mcap = None
                    # Backlog #76 — book value per share. The pre-4.x code read
                    # this straight from the ratio sheet ('BVPS (VND)'); the 4.x
                    # rewrite dropped it and nothing noticed for four months
                    # because its only test was among the eleven that were red.
                    #
                    # Restored by asking the vendor again under every name it
                    # might use, rather than by deriving it. (pe x eps) / pb is
                    # algebraically tempting and WRONG here: `eps` is quarterly
                    # while P/E is trailing, so the implied price — and the BVPS
                    # that falls out of it — would be off by roughly a factor of
                    # four. A wrong book value is worse than an absent one.
                    bvps = self._pick(
                        latest,
                        'BVPS (VND)', 'BVPS', 'Book value per share',
                        'Book Value Per Share (VND)', 'Book value per share (VND)',
                    )
                    # Backlog #76 + #97 — ONE KBS call now serves both: the
                    # BVPS that VCI supplies under no name, and every
                    # ratio-derived field, because VCI's `ratio()` is eight
                    # years stale (see KBS_RATIO_FIELDS). Previously two
                    # separate concerns; merging them keeps the cost at one
                    # extra vnstock call per invocation, which matters against
                    # the 20 req/min guest quota (#49).
                    #
                    # Best-effort: if KBS is unavailable the ratio fields stay
                    # unset. VCI's stale values are deliberately NOT a
                    # fallback — a wrong number is worse than an absent one.
                    try:
                        kbs_ratio = await vnstock_call(
                            self.vnstock.stock(
                                symbol=symbol.upper(), source="KBS"
                            ).finance.ratio,
                            period="year",
                        )
                        if bvps is None:
                            bvps = bvps_from_ratio_frame(kbs_ratio)
                        kbs_metrics, ratios_as_of = ratio_metrics_from_kbs(kbs_ratio)
                        if kbs_metrics:
                            pe = kbs_metrics.get("pe_ratio", None)
                            pb = kbs_metrics.get("pb_ratio", None)
                            ps = kbs_metrics.get("ps_ratio", None)
                            roe = kbs_metrics.get("roe", None)
                            roa = kbs_metrics.get("roa", None)
                            de = kbs_metrics.get("debt_to_equity", None)
                            cr = kbs_metrics.get("current_ratio", None)
                            qr = kbs_metrics.get("quick_ratio", None)
                            gm = kbs_metrics.get("gross_margin", None)
                            om = kbs_metrics.get("operating_margin", None)
                            npm = kbs_metrics.get("profit_margin", None)
                            ev_ebitda = kbs_metrics.get("ev_ebitda", None)
                            div_yield = kbs_metrics.get("dividend_yield", None)
                            financials.ratios_as_of = ratios_as_of
                        else:
                            pe = pb = ps = roe = roa = de = cr = qr = None
                            gm = om = npm = ev_ebitda = div_yield = None
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "KBS ratio lookup failed for %s: %s: %s — ratio "
                            "fields left unset rather than served stale",
                            symbol, type(exc).__name__, exc,
                        )
                        pe = pb = ps = roe = roa = de = cr = qr = None
                        gm = om = npm = ev_ebitda = div_yield = None
                    # Vendor-reported debt/assets if offered; otherwise derived
                    # from the balance sheet further down.
                    debt_to_assets = self._pick(
                        latest, 'Debt to Assets', 'Debt/Assets', 'Total Debt/Total Assets',
                    )

                    # Set flat fields
                    financials.pe_ratio = pe
                    financials.pb_ratio = pb
                    financials.ps_ratio = ps
                    financials.roe = roe
                    financials.roa = roa
                    financials.debt_to_equity = de
                    financials.current_ratio = cr
                    financials.quick_ratio = qr
                    financials.gross_margin = gm
                    financials.operating_margin = om
                    financials.profit_margin = npm
                    financials.ev_ebitda = ev_ebitda
                    financials.dividend_yield = div_yield
                    financials.market_cap = mcap
                    financials.book_value_per_share = bvps
                    financials.debt_to_assets = debt_to_assets

                    # Set nested financial_ratios
                    financial_ratios.pe = pe
                    financial_ratios.pb = pb
                    financial_ratios.ps = ps
                    financial_ratios.roe = roe
                    financial_ratios.roa = roa
                    financial_ratios.debtToEquity = de
                    financial_ratios.currentRatio = cr
                    financial_ratios.quickRatio = qr
                    financial_ratios.grossMargin = gm
                    financial_ratios.operatingMargin = om
                    financial_ratios.netMargin = npm

                    logger.info(f"Fetched financial ratios for {symbol}: PE={pe}, ROE={roe}")

            except Exception as ratio_error:
                logger.warning(f"Could not fetch financial ratios for {symbol}: {ratio_error}")

            # Try to get income statement for revenue, net income, and growth
            try:
                is_df = stock.finance.income_statement(period="quarter", lang="en")
                latest_is = self._latest_metrics(is_df)

                if latest_is:
                    # Get revenue and income data (long-format item_en values)
                    revenue = self._pick(latest_is, 'Net sales', 'Sales', 'Revenue',
                                         'Net Interest Income')  # banks
                    gross_profit = self._pick(latest_is, 'Gross Profit')
                    operating_income = self._pick(latest_is, 'Operating profit/(loss)')
                    net_income = self._pick(latest_is, 'Attributable to parent company',
                                            'Net profit/(loss) after tax')
                    eps = self._pick(latest_is, 'EPS basic (VND)', 'EPS diluted (VND)')

                    # Year-over-year growth from a same-quarter-prior-year column, when present
                    revenue_yoy = self._yoy(is_df, 'Net sales', 'Sales', 'Revenue', 'Net Interest Income')
                    earnings_yoy = self._yoy(is_df, 'Attributable to parent company',
                                             'Net profit/(loss) after tax')
                    eps_yoy = self._yoy(is_df, 'EPS basic (VND)')

                    # Set income statement
                    income_statement.revenue = revenue
                    income_statement.grossProfit = gross_profit
                    income_statement.operatingIncome = operating_income
                    income_statement.netIncome = net_income
                    income_statement.eps = eps

                    # Set flat fields
                    financials.eps = eps
                    financials.revenue_growth = revenue_yoy
                    financials.earnings_growth = earnings_yoy

                    # Set growth metrics
                    growth_metrics.revenueGrowth = revenue_yoy
                    growth_metrics.earningsGrowth = earnings_yoy
                    growth_metrics.epsGrowth = eps_yoy

                    logger.info(f"Fetched income statement for {symbol}: Revenue={revenue}, NetIncome={net_income}")

            except Exception as is_error:
                logger.warning(f"Could not fetch income statement for {symbol}: {is_error}")

            # Try to get balance sheet for assets, liabilities, equity
            try:
                bs_df = stock.finance.balance_sheet(period="quarter", lang="en")
                latest_bs = self._latest_metrics(bs_df)

                if latest_bs:
                    total_assets = self._pick(latest_bs, 'Total Assets', 'TOTAL ASSETS')
                    # 'Cash and precious metals' is the bank spelling (TCB).
                    cash = self._pick(
                        latest_bs, 'Cash and cash equivalents', 'Cash and precious metals',
                    )
                    total_equity = self._pick(latest_bs, "Owner's Equity", 'Total Equity')
                    total_liabilities = self._pick(latest_bs, 'Liabilities', 'Total Liabilities')
                    long_term_debt = self._pick(latest_bs, 'Long-term liabilities', 'Long-term borrowings')

                    # Fall back to assets - equity if liabilities not reported directly
                    if total_liabilities is None and total_assets and total_equity:
                        total_liabilities = total_assets - total_equity

                    balance_sheet.totalAssets = total_assets
                    balance_sheet.totalLiabilities = total_liabilities
                    balance_sheet.totalEquity = total_equity
                    balance_sheet.cash = cash
                    balance_sheet.longTermDebt = long_term_debt

                    # Backlog #76 — two fields the 4.x rewrite left unset even
                    # though every input is already in hand.
                    #
                    # debt_to_assets: a ratio, matching debt_to_equity's units.
                    # Both terms come from the SAME balance sheet, so the figure
                    # is internally consistent — but be aware it will not
                    # reconcile with the vendor's debt_to_equity, which is
                    # computed on a different basis (for FPT the vendor reports
                    # P/B 2.44 where market_cap/equity is 0.75, so the ratio
                    # sheet and the balance sheet are not the same consolidation).
                    if financials.debt_to_assets is None and total_liabilities is not None and total_assets:
                        financials.debt_to_assets = total_liabilities / total_assets

                    # enterprise_value = market cap + debt - cash. Mixing market
                    # value with balance-sheet debt is inherent to EV, not a
                    # unit error. CAVEAT: only long-term liabilities are
                    # available here, so short-term borrowings are omitted and
                    # this is a LOWER BOUND on EV.
                    #
                    # A real debt figure is REQUIRED rather than defaulted to
                    # zero (tightened at #77). Banks report no "long-term
                    # liabilities" line at all — their funding is customer
                    # deposits — so defaulting would have published
                    # "market cap - cash" and labelled it enterprise value for
                    # every bank. EV is not a conventional measure for banks
                    # anyway, so declining to compute it is the right answer,
                    # not a gap.
                    # Backlog #97 — market cap from a LIVE price, not the
                    # fiscal-year one.
                    #
                    # The vendor's figure was ~3x stale (26.57T for FPT against
                    # roughly 84T). The obvious replacement, `P/B x book
                    # equity`, is algebraically exact but prices at FISCAL YEAR
                    # END: FPT fell from ~96k to 57k during 2025, which put it
                    # at 152.9T — 1.8x too HIGH, i.e. no better in relative
                    # error than the stale figure it replaced. Measured, not
                    # assumed.
                    #
                    # So an absolute currency figure is stated CURRENTLY while
                    # the ratios stay on their fiscal basis. That is the
                    # conventional presentation, not a fudge: ratios are
                    # reported per fiscal year, market cap as of now.
                    #
                    #   shares = book equity / BVPS   (same KBS sheet, so the
                    #                                  period cancels)
                    #   market cap = live close x shares
                    if (financials.market_cap is None and total_equity
                            and financials.book_value_per_share):
                        try:
                            shares = total_equity / financials.book_value_per_share
                            price = await self._latest_close(symbol)
                            if price and shares > 0:
                                financials.market_cap = price * shares
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "live market cap for %s failed: %s: %s — left "
                                "unset rather than stated on a stale basis",
                                symbol, type(exc).__name__, exc,
                            )

                    if financials.market_cap and cash is not None and long_term_debt is not None:
                        financials.enterprise_value = (
                            financials.market_cap + long_term_debt - cash
                        )

                    logger.info(f"Fetched balance sheet for {symbol}: Assets={total_assets}, Cash={cash}")

            except Exception as bs_error:
                logger.warning(f"Could not fetch balance sheet for {symbol}: {bs_error}")

            # Try to get cash flow statement
            try:
                cf_df = stock.finance.cash_flow(period="quarter", lang="en")
                latest_cf = self._latest_metrics(cf_df)

                if latest_cf:
                    operating_cf = self._pick(latest_cf, 'Net cash inflows/(outflows) from operating activities',
                                              'Net cash from operating activities')  # banks
                    investing_cf = self._pick(latest_cf, 'Net cash inflows/(outflows) from investing activities',
                                              'Net cash from investing activities')  # banks
                    financing_cf = self._pick(latest_cf, 'Net cash inflows/(outflows) from financing activities',
                                              'Net cash from financing activities')  # banks
                    net_cf = self._pick(latest_cf, 'Net increase in cash and cash equivalents',
                                        'Net increase/decrease in cash and cash equivalents')

                    cash_flow.operatingCashFlow = operating_cf
                    cash_flow.investingCashFlow = investing_cf
                    cash_flow.financingCashFlow = financing_cf
                    cash_flow.netCashFlow = net_cf

                    # Calculate free cash flow (Operating - CapEx); capex is reported negative
                    capex = self._pick(latest_cf, 'Purchases of fixed assets and other long term assets',
                                       'Purchase of fixed assets')
                    if operating_cf is not None and capex is not None:
                        cash_flow.freeCashFlow = operating_cf + capex

                    logger.info(f"Fetched cash flow for {symbol}: Operating={operating_cf}, Net={net_cf}")

            except Exception as cf_error:
                logger.warning(f"Could not fetch cash flow for {symbol}: {cf_error}")

            # Set nested structures
            financials.financial_ratios = financial_ratios
            financials.growth_metrics = growth_metrics
            financials.income_statement = income_statement
            financials.balance_sheet = balance_sheet
            financials.cash_flow = cash_flow

            return financials

        except Exception as e:
            logger.error(f"Error fetching financials for {symbol}: {e}")
            return None

    @staticmethod
    def _period_columns(df: pd.DataFrame) -> List[str]:
        """Return the period columns (e.g. '2026-Q1', '2025') in a long-format
        vnstock financial statement, ordered newest-first."""
        cols = [str(c) for c in df.columns
                if re.match(r"^\d{4}-Q\d$", str(c)) or re.match(r"^\d{4}$", str(c))]

        def key(p: str):
            year = int(p[:4])
            quarter = int(p.split("Q")[-1]) if "Q" in p else 0
            return (year, quarter)

        return sorted(cols, key=key, reverse=True)

    def _latest_metrics(self, df: Optional[pd.DataFrame]) -> dict:
        """Collapse a long-format vnstock statement (one metric per row in the
        'item_en' column, one column per period) into a {metric_name: value}
        dict for the most recent reported period.

        vnstock 4.x returns statements transposed versus older versions, and the
        period ordering differs across statements, so we select the latest period
        by parsing the column labels rather than relying on position.
        """
        if df is None or df.empty or "item_en" not in df.columns:
            return {}
        periods = self._period_columns(df)
        if not periods:
            return {}
        latest = periods[0]
        metrics = {}
        for name, value in zip(df["item_en"], df[latest]):
            if name is None or pd.isna(value):
                continue
            metrics.setdefault(str(name), value)  # keep first occurrence
        return metrics

    @staticmethod
    def _pick(metrics: dict, *names: str) -> Optional[float]:
        """Return the first available numeric value among the given metric names.

        Matching is CASE-INSENSITIVE (Backlog #77). Banks and non-banks spell
        the same line differently in case alone: FPT reports ``Liabilities``
        and ``Owner's Equity`` where TCB reports ``TOTAL LIABILITIES`` and
        ``OWNER'S EQUITY``. Exact dict lookup therefore left bank balance
        sheets ~80% empty — only ``TOTAL ASSETS`` matched, because that
        spelling happened to be listed explicitly.

        Verified safe before relaxing it: across FPT's 122 rows and TCB's 86,
        no two differently-spelled labels collapse to the same lowercase, so
        case-folding cannot make one metric shadow another.
        """
        folded = {}
        for key, value in metrics.items():
            folded.setdefault(str(key).strip().lower(), value)
        for name in names:
            for candidate in (metrics.get(name), folded.get(str(name).strip().lower())):
                if candidate is None:
                    continue
                try:
                    value = float(candidate)
                    if pd.notna(value):
                        return value
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _as_percent(value: Optional[float]) -> Optional[float]:
        """vnstock reports margins/returns as fractions (0.41 == 41%); scale to %."""
        if value is None:
            return None
        return value * 100 if abs(value) < 1 else value

    def _yoy(self, df: Optional[pd.DataFrame], *names: str) -> Optional[float]:
        """Year-over-year growth (%) for a metric, computed from the latest period
        and the same quarter one year earlier, when both columns are present."""
        if df is None or df.empty or "item_en" not in df.columns:
            return None
        periods = self._period_columns(df)
        if not periods:
            return None
        latest = periods[0]
        m = re.match(r"^(\d{4})(-Q\d)?$", latest)
        if not m:
            return None
        prior = f"{int(m.group(1)) - 1}{m.group(2) or ''}"
        if prior not in [str(c) for c in df.columns]:
            return None
        cur = self._pick(self._latest_metrics(df), *names)
        prior_row = dict(zip(df["item_en"].astype(str), df[prior]))
        prev = self._pick(prior_row, *names)
        if cur is None or prev in (None, 0):
            return None
        return (cur - prev) / abs(prev) * 100

    def _get_ratio_value(self, row: pd.Series, possible_names: list) -> Optional[float]:
        """
        Helper to extract a ratio value from a DataFrame row.
        Tries multiple possible column names.
        """
        for name in possible_names:
            if name in row.index:
                value = row[name]
                if pd.notna(value):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        return None

    def _get_multilevel_value(self, row: pd.Series, metric_name: str) -> Optional[float]:
        """
        Helper to extract a value from a DataFrame row with multi-level columns.
        vnstock uses tuple column names like ('Category', 'Metric Name').
        """
        for col in row.index:
            # Handle tuple column names
            if isinstance(col, tuple):
                if metric_name in col[1] or col[1] == metric_name:
                    value = row[col]
                    if pd.notna(value):
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            continue
            # Handle simple column names
            elif col == metric_name or metric_name in str(col):
                value = row[col]
                if pd.notna(value):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        return None

    def _get_simple_value(self, row: pd.Series, col_name: str) -> Optional[float]:
        """
        Helper to extract a value from a DataFrame row with simple column names.
        Tries exact match first, then partial match.
        """
        # Try exact match
        if col_name in row.index:
            value = row[col_name]
            if pd.notna(value):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    pass

        # Try partial match
        for col in row.index:
            if col_name.lower() in str(col).lower():
                value = row[col]
                if pd.notna(value):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        continue
        return None
