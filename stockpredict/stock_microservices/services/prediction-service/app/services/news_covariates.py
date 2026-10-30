"""services/ — attach news covariates to a solution's feature frame (Backlog #106).

Pure except for one explicitly-async fetch, so the merge logic is testable
offline. The series themselves are built by news-service
(`GET /news/features/{symbol}`); this module only joins them onto the trading
calendar the price data defines.

WHY 0.0 AND NOT NaN for a date with no news. `_run_training` calls `dropna()`
on the whole frame, and that drop is governed by the longest-warm-up column, so
a NaN-filled news column would silently delete every bar outside the news
window — on this corpus that is most of the history (Backlog #110 made that
cost visible for indicators; the same trap applies here). 0.0 is also the
correct value rather than a convenience: intensity 0 means no coverage decayed
into this date, and polarity 0 means no trustworthy tone in memory. Those two
travel together precisely so the pair stays readable — intensity says whether
there was news at all, which is what a lone polarity column cannot express.

PAST COVARIATES ONLY. Tomorrow's coverage is not knowable today
(#104/#105, CLAUDE.md C1). Both columns land in `feature_df`, where
`_run_darts_engine` maps every feature column to a past covariate, so they
inherit that guarantee rather than restating it.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Sequence

import pandas as pd

logger = logging.getLogger(__name__)

# The columns this module adds. Named here so the trainer, the tests and the
# payload all agree on one spelling.
NEWS_FEATURE_COLUMNS = ("news_intensity", "news_polarity")


class NewsCovariateError(RuntimeError):
    """news-service could not supply the series that was explicitly asked for."""


def attach_news_features(
    feature_df: pd.DataFrame, rows: Sequence[Mapping[str, Any]]
) -> pd.DataFrame:
    """Return `feature_df` with the two news columns joined on by date.

    `rows` are the calendar-daily records from news-service. The frame's index is
    the TRADING calendar, so this is a reindex: weekend rows are dropped and
    their decayed weight has already been carried into the next trading day by
    the recursion upstream — which is why the decay is computed over calendar
    days there rather than over bars here.

    Missing dates become 0.0, never NaN (see the module docstring).
    """
    out = feature_df.copy()
    if not len(out):
        for col in NEWS_FEATURE_COLUMNS:
            out[col] = pd.Series(dtype="float64")
        return out

    by_date: dict[Any, Mapping[str, Any]] = {}
    for r in rows or ():
        key = pd.to_datetime(r.get("date"), errors="coerce")
        if pd.isna(key):
            continue
        by_date[key.normalize()] = r

    idx_dates = pd.DatetimeIndex(out.index).normalize()
    out["news_intensity"] = [
        float(by_date.get(d, {}).get("intensity", 0.0) or 0.0) for d in idx_dates
    ]
    out["news_polarity"] = [
        float(by_date.get(d, {}).get("polarity", 0.0) or 0.0) for d in idx_dates
    ]
    return out


def news_coverage(feature_df: pd.DataFrame) -> dict:
    """What the news columns actually contribute, for the training payload.

    Reported rather than assumed: on a corpus covering four symbols over seven
    weeks, these columns are zero for almost every bar, and a model trained on
    them should say so instead of implying a feature that carries signal.
    """
    if not all(c in feature_df.columns for c in NEWS_FEATURE_COLUMNS):
        return {"attached": False}
    intensity = feature_df["news_intensity"]
    polarity = feature_df["news_polarity"]
    n = int(len(feature_df))
    nonzero = int((intensity > 0).sum())
    return {
        "attached": True,
        "rows": n,
        "rows_with_coverage": nonzero,
        "coverage_fraction": round(nonzero / n, 4) if n else 0.0,
        "intensity_max": round(float(intensity.max()), 4) if n else 0.0,
        "polarity_nonzero_rows": int((polarity != 0).sum()),
        # Stated plainly so a flat feature is never read as "the news was calm".
        "note": (
            "news_intensity and news_polarity are PAST covariates. 0.0 means no "
            "coverage decayed into that bar, not neutral news. polarity ignores "
            "rows whose score provenance is untrusted (pre-#112 or template), so "
            "a zero polarity beside a positive intensity means coverage existed "
            "but its tone is not trustworthy — see Backlog #113."
        ),
    }


async def fetch_news_features(
    client, *, base_url: str, api_prefix: str, symbol: str,
    start: str, end: str, halflife_days: float,
) -> list[dict]:
    """GET the decayed series for one symbol. Raises NewsCovariateError on failure.

    Raising rather than returning [] is deliberate: the caller asked for news
    features, and silently training without them would report a model built on
    features it never saw — the same class of defect as a solution labelled 'TFT'
    that trains as LightGBM (#109).
    """
    url = f"{base_url.rstrip('/')}/{api_prefix}/api/v2/news/news/features/{symbol.upper()}"
    params = {"start": start, "end": end, "halflife_days": halflife_days}
    try:
        resp = await client.get(url, params=params)
    except Exception as exc:  # noqa: BLE001 — any transport failure is the same to us
        raise NewsCovariateError(f"news-service unreachable: {exc}") from exc
    if resp.status_code != 200:
        raise NewsCovariateError(
            f"news-service returned HTTP {resp.status_code} for {symbol}"
        )
    body = resp.json() or {}
    rows = body.get("data")
    if not isinstance(rows, list):
        raise NewsCovariateError("news-service response carried no 'data' list")
    return rows
