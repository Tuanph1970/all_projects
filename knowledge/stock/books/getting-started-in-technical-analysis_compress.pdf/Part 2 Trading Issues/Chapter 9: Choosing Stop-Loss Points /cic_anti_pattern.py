"""
CIC Anti-Pattern — Chapter 9, Concept 9
==========================================
"Cancel If Close" — the behavioral failure mode of canceling stops
when price approaches them. Defeats the entire purpose of the stop.

Schwager: "Revising the stop to allow greater risk defeats the
entire purpose of the stop."

This module provides:
  - detect_cic_behavior: identify if a stop modification increases risk
  - simulate_cic_vs_discipline: backtest the cost of CIC behavior
"""

import random


def detect_cic_behavior(
    original_stop: float,
    new_stop: float,
    is_long: bool = True,
) -> dict:
    """
    Detect if a stop modification is CIC behavior (increasing risk).
    
    Returns:
        dict with 'is_cic', 'original_stop', 'new_stop', 'warning'
    """
    if is_long:
        is_cic = new_stop < original_stop
    else:
        is_cic = new_stop > original_stop

    return {
        "is_cic": is_cic,
        "original_stop": original_stop,
        "new_stop": new_stop,
        "risk_change": "INCREASED" if is_cic else "decreased",
        "warning": (
            f"CIC DETECTED: moving {'long' if is_long else 'short'} stop "
            f"from {original_stop:.2f} to {new_stop:.2f} INCREASES risk. "
            f"This defeats the purpose of the stop."
        ) if is_cic else "Stop tightened — acceptable.",
    }


def simulate_cic_vs_discipline(
    n_trials: int = 1000,
    stop_pct: float = 5.0,
    seed_base: int = 42,
) -> dict:
    """
    Simulate the cost of CIC behavior vs disciplined stop execution.
    
    In the CIC scenario, when price comes within 1% of the stop,
    the trader cancels it and holds.
    
    Returns:
        Performance comparison between both approaches.
    """
    disc_pnls = []
    cic_pnls = []

    for t in range(n_trials):
        random.seed(seed_base + t)
        entry = 100.0
        stop = entry * (1 - stop_pct / 100)

        prices = [entry]
        drift = -0.1 + random.random() * 0.15
        for i in range(120):
            vol = 1.8 + random.random() * 1.2
            prices.append(max(10, prices[-1] + drift + vol * (random.gauss(0, 1) - 0.05)))

        # Disciplined: execute stop as designed
        disc_exit = prices[-1]
        for p in prices[1:]:
            if p <= stop:
                disc_exit = p
                break
        disc_pnls.append((disc_exit - entry) / entry * 100)

        # CIC: cancel stop when price gets within 1% of it, then hold
        cic_exit = prices[-1]  # always hold to end (stop was canceled)
        cic_pnls.append((cic_exit - entry) / entry * 100)

    def stats(pnls):
        pnls_sorted = sorted(pnls)
        n = len(pnls_sorted)
        return {
            "avg": round(sum(pnls) / n, 2),
            "median": round(pnls_sorted[n // 2], 2),
            "worst": round(pnls_sorted[0], 2),
            "p5": round(pnls_sorted[int(n * 0.05)], 2),
            "pct_losing": round(sum(1 for p in pnls if p < 0) / n * 100, 1),
            "pct_catastrophic": round(sum(1 for p in pnls if p < -20) / n * 100, 1),
        }

    return {
        "disciplined": stats(disc_pnls),
        "cic": stats(cic_pnls),
        "n_trials": n_trials,
        "stop_pct": stop_pct,
    }


if __name__ == "__main__":
    # 1. Detect CIC behavior
    print("--- CIC detection ---")
    result = detect_cic_behavior(original_stop=95.0, new_stop=92.0, is_long=True)
    print(f"  {result['warning']}")

    result = detect_cic_behavior(original_stop=95.0, new_stop=97.0, is_long=True)
    print(f"  {result['warning']}")

    # 2. CIC vs discipline
    print("\n--- CIC vs disciplined (1000 trials, 5% stop) ---")
    comp = simulate_cic_vs_discipline()
    print(f"{'Metric':<20} {'Disciplined':>12} {'CIC':>12}")
    print("-" * 46)
    for key in ["avg", "median", "worst", "p5", "pct_losing", "pct_catastrophic"]:
        label = {
            "avg": "Avg P&L",
            "median": "Median P&L",
            "worst": "Worst case",
            "p5": "5th percentile",
            "pct_losing": "% losing",
            "pct_catastrophic": "% loss > 20%",
        }[key]
        d = comp["disciplined"][key]
        c = comp["cic"][key]
        suffix = "%" if "pct" in key else "%"
        print(f"{label:<20} {d:>+11.1f}% {c:>+11.1f}%")
