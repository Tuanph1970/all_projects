"""
Money Stops — Chapter 9, Concept 7
====================================
A fixed-dollar (or fixed-percentage) stop with NO technical significance.
Used as a fallback when chart-based stops imply excessive risk.

Schwager: "A protective stop-loss point with no technical significance
that is determined by the desired dollar risk level."

This module provides:
  - MoneyStop: dataclass for fixed-risk stops
  - should_use_money_stop: decision function for chart vs money stop
  - compare_money_vs_chart_stop: backtest quantifying the tradeoff
"""

from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class MoneyStop:
    """A fixed-risk stop with no technical basis."""
    entry_price: float
    max_risk_pct: float = 5.0
    is_long: bool = True

    @property
    def stop_price(self) -> float:
        distance = self.entry_price * self.max_risk_pct / 100
        return self.entry_price - distance if self.is_long else self.entry_price + distance

    @property
    def risk_pct(self) -> float:
        return self.max_risk_pct


def should_use_money_stop(
    chart_stop_risk_pct: float,
    max_acceptable_risk_pct: float = 10.0,
) -> dict:
    """Determine whether chart-based stop risk is excessive."""
    excessive = chart_stop_risk_pct > max_acceptable_risk_pct
    return {
        "use_money_stop": excessive,
        "chart_risk_pct": chart_stop_risk_pct,
        "max_risk_pct": max_acceptable_risk_pct,
        "reason": (
            f"Chart stop implies {chart_stop_risk_pct:.1f}% risk, "
            f"exceeding max {max_acceptable_risk_pct:.1f}%. Use money stop."
            if excessive else "Chart stop risk is acceptable."
        ),
    }


def compare_money_vs_chart_stop(
    n_trials: int = 500,
    money_risk_pct: float = 5.0,
    chart_risk_pct: float = 15.0,
    seed_base: int = 17,
) -> dict:
    """
    Backtest comparing a tight money stop vs a wide chart-based stop.
    Demonstrates the tradeoff: money stops keep risk known but may
    exit without technical reason.
    """
    money_pnls, chart_pnls = [], []
    money_false = chart_false = money_stopped = chart_stopped = 0

    for t in range(n_trials):
        random.seed(seed_base + t * 29)
        entry = 100.0
        m_stop = entry * (1 - money_risk_pct / 100)
        c_stop = entry * (1 - chart_risk_pct / 100)

        prices = [entry]
        is_bull = random.random() < 0.55
        for i in range(80):
            drift = 0.15 if is_bull else -0.2
            vol = 1.5 + random.random() * 0.8
            prices.append(prices[-1] + drift + vol * random.gauss(0, 1))

        for stop, pnls, label in [(m_stop, money_pnls, 'money'), (c_stop, chart_pnls, 'chart')]:
            stopped = False
            for i in range(1, len(prices)):
                if prices[i] <= stop:
                    pnls.append((prices[i] - entry) / entry * 100)
                    if label == 'money': money_stopped += 1
                    else: chart_stopped += 1
                    future = prices[i+1:min(i+25, len(prices))]
                    if any(p > entry for p in future):
                        if label == 'money': money_false += 1
                        else: chart_false += 1
                    stopped = True; break
            if not stopped:
                pnls.append((prices[-1] - entry) / entry * 100)

    def stats(pnls, stopped, false_ct):
        return {
            "avg_pnl": round(sum(pnls)/len(pnls), 2),
            "worst_pnl": round(min(pnls), 2),
            "false_stop_rate": round(false_ct/max(stopped,1)*100, 1),
            "times_stopped": stopped,
        }

    return {
        "money_stop": {"risk_pct": money_risk_pct, **stats(money_pnls, money_stopped, money_false)},
        "chart_stop": {"risk_pct": chart_risk_pct, **stats(chart_pnls, chart_stopped, chart_false)},
    }


if __name__ == "__main__":
    ms = MoneyStop(entry_price=100.0, max_risk_pct=5.0)
    print(f"Money stop: entry={ms.entry_price}, stop={ms.stop_price:.1f}, risk={ms.risk_pct:.1f}%")

    result = should_use_money_stop(chart_stop_risk_pct=15.0, max_acceptable_risk_pct=10.0)
    print(f"Decision: {result['reason']}")

    print("\n--- Money stop (5%) vs chart stop (15%) ---")
    comp = compare_money_vs_chart_stop()
    for name, data in comp.items():
        label = name.replace('_', ' ').title()
        print(f"  {label} ({data['risk_pct']}%): avg={data['avg_pnl']:+.1f}%, "
              f"worst={data['worst_pnl']:+.1f}%, false={data['false_stop_rate']:.1f}%, "
              f"stopped={data['times_stopped']}")
