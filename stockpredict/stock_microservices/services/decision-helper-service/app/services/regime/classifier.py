"""F-012 — Regime classifier.

Fetches the regime feature vector from analysis-service and maps it to
the internal TREND_UP / TREND_DOWN / RANGE / UNDEFINED enum used by the
signal pipeline.

Mapping rule (consistent with ADR-001 §4.1):
  analysis-service "TREND"  → TREND_UP  if slope >= 0 else TREND_DOWN
  analysis-service "RANGE"  → RANGE
  analysis-service "UNDEFINED" → UNDEFINED
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.services.market.client import MarketClient

logger = logging.getLogger(__name__)


@dataclass
class RegimeResult:
    regime: str                         # TREND_UP | TREND_DOWN | RANGE | UNDEFINED
    confidence: float                   # 0..1
    features: Dict[str, float] = field(default_factory=dict)
    source_regime: str = "UNDEFINED"    # raw value from analysis-service


async def classify_regime(symbol: str, client: MarketClient) -> RegimeResult:
    """Call analysis-service and return a RegimeResult."""
    data = await client.fetch_regime(symbol)
    if data is None:
        logger.warning("Regime fetch failed for %s — defaulting UNDEFINED", symbol)
        return RegimeResult(regime="UNDEFINED", confidence=0.0)

    raw_regime: str = data.get("regime", "UNDEFINED")
    confidence: float = float(data.get("confidence", 0.0))
    features_raw: Dict = data.get("features", {})

    features = {
        "slope": float(features_raw.get("slope", 0.0)),
        "hh_hl_count": float(features_raw.get("hh_hl_count", 0)),
        "adx": float(features_raw.get("adx", 0.0)),
        "range_atr_ratio": float(features_raw.get("range_atr_ratio", 0.0)),
    }

    if raw_regime == "TREND":
        # Use slope sign to split into directional regimes
        regime = "TREND_UP" if features["slope"] >= 0 else "TREND_DOWN"
    elif raw_regime == "RANGE":
        regime = "RANGE"
    else:
        regime = "UNDEFINED"

    return RegimeResult(
        regime=regime,
        confidence=confidence,
        features=features,
        source_regime=raw_regime,
    )
