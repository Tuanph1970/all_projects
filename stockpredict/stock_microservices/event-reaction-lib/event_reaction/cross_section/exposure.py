"""cross_section/ — CAR-on-surprise exposure regression (FR-XS, FR-CLUSTER, EC2, EC3).

Pure stats stage: NO I/O. The regressor is the SURPRISE, never the raw event (EC2).
When events cluster on the same day their abnormal returns are cross-sectionally
correlated, so the iid event-study t-test over-rejects (EC3). Inference modes:

    cluster="event_date" (default) : SEs clustered by event date (statsmodels)
    cluster="portfolio"            : collapse same-day events to one obs, then OLS
    cluster="iid"                  : ordinary OLS SEs — WRONG under clustering; provided
                                     only to demonstrate the over-rejection (tests/EC3)

The standardised cross-sectional (Boehmer-Musumeci-Poulsen / Kolari-Pynnonen) variant
is a documented future option; the two robust routes above are sufficient for EC3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from event_reaction.exceptions import InsufficientDataError
from event_reaction.types import CrossSectionExposure

_REQUIRED = {"surprise", "car", "event_date"}


def cross_sectional_exposure(
    panel: pd.DataFrame,
    *,
    cluster: str = "event_date",
) -> CrossSectionExposure:
    """Regress ``car ~ surprise`` across assets with clustering-robust inference.

    Parameters
    ----------
    panel : DataFrame with columns ``surprise``, ``car``, ``event_date`` (and optionally
        ``asset``). Each row is one asset's reaction to an event.
    cluster : "event_date" (default) | "portfolio" | "iid".
    """
    missing = _REQUIRED - set(panel.columns)
    if missing:
        raise InsufficientDataError(f"panel missing columns: {sorted(missing)}")
    if len(panel) < 3:
        raise InsufficientDataError("need at least 3 observations for the regression")

    n_assets = int(panel["asset"].nunique()) if "asset" in panel.columns else len(panel)
    n_event_dates = int(panel["event_date"].nunique())

    if cluster == "portfolio":
        agg = panel.groupby("event_date", sort=True)[["surprise", "car"]].mean()
        X = sm.add_constant(agg["surprise"])
        res = sm.OLS(agg["car"], X).fit()
    elif cluster == "event_date":
        X = sm.add_constant(panel["surprise"])
        res = sm.OLS(panel["car"], X).fit(
            cov_type="cluster", cov_kwds={"groups": panel["event_date"].to_numpy()}
        )
    elif cluster == "iid":
        X = sm.add_constant(panel["surprise"])
        res = sm.OLS(panel["car"], X).fit()
    else:
        raise ValueError(f"unknown cluster mode {cluster!r}")

    return CrossSectionExposure(
        gamma0=float(res.params["const"]),
        gamma1=float(res.params["surprise"]),
        se_gamma1=float(res.bse["surprise"]),
        cluster=cluster,
        n_assets=n_assets,
        n_event_dates=n_event_dates,
        r_squared=float(res.rsquared),
    )
