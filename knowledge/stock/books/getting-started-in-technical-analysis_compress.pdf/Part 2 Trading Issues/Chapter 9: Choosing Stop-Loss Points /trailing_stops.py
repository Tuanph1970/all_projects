"""
Trailing Stops — Chapter 9, Concept 8
=======================================
Two flavors: chart-based (relative lows) and fixed-distance trailing.
"""

import random


def chart_based_trailing_stop(prices, entry_bar, n=10):
    """Trail using relative lows (Walt Disney method)."""
    entry_price = prices[entry_bar]
    highest = entry_price
    current_stop = None
    stop_history = []

    rel_lows = []
    for i in range(n, len(prices) - n):
        window = prices[i - n: i + n + 1]
        if prices[i] == min(window):
            rel_lows.append((i, prices[i]))

    prior = [l for l in rel_lows if l[0] < entry_bar]
    if prior:
        current_stop = prior[-1][1]
        stop_history.append({"bar": entry_bar, "stop": current_stop})

    for i in range(entry_bar + 1, len(prices)):
        if current_stop is not None and prices[i] <= current_stop:
            pnl = (prices[i] - entry_price) / entry_price * 100
            return {"stop_history": stop_history, "exit_bar": i,
                    "pnl_pct": round(pnl, 2), "n_raises": len(stop_history)}
        if prices[i] > highest:
            highest = prices[i]
            candidates = [l for l in rel_lows if l[0] > entry_bar and l[0] < i and l[1] > (current_stop or 0)]
            if candidates and candidates[-1][1] != current_stop:
                current_stop = candidates[-1][1]
                stop_history.append({"bar": i, "stop": current_stop})

    pnl = (prices[-1] - entry_price) / entry_price * 100
    return {"stop_history": stop_history, "exit_bar": len(prices) - 1,
            "pnl_pct": round(pnl, 2), "n_raises": len(stop_history)}


def fixed_trailing_stop(prices, entry_bar, trail_pct=5.0):
    """Trail by fixed percentage below the high-water mark."""
    entry_price = prices[entry_bar]
    highest = entry_price
    current_stop = entry_price * (1 - trail_pct / 100)

    for i in range(entry_bar + 1, len(prices)):
        if prices[i] <= current_stop:
            pnl = (prices[i] - entry_price) / entry_price * 100
            return {"exit_bar": i, "pnl_pct": round(pnl, 2), "trail_pct": trail_pct}
        if prices[i] > highest:
            highest = prices[i]
            new_stop = highest * (1 - trail_pct / 100)
            if new_stop > current_stop:
                current_stop = new_stop

    pnl = (prices[-1] - entry_price) / entry_price * 100
    return {"exit_bar": len(prices) - 1, "pnl_pct": round(pnl, 2), "trail_pct": trail_pct}


def compare_trailing_methods(n_trials=500, seed_base=31):
    """Backtest chart-based vs fixed trailing stops."""
    chart_pnls, fixed_pnls = [], []
    for t in range(n_trials):
        random.seed(seed_base + t * 19)
        prices = [100.0]
        for i in range(1, 140):
            drift = 0.22 if i < 90 else -0.18
            vol = 1.2 + random.random() * 1.0
            prices.append(prices[-1] + drift + vol * (random.gauss(0, 1) - 0.02))
        chart_pnls.append(chart_based_trailing_stop(prices, 15, 10)["pnl_pct"])
        fixed_pnls.append(fixed_trailing_stop(prices, 15, 5.0)["pnl_pct"])

    def stats(pnls):
        return {"avg": round(sum(pnls)/len(pnls), 2),
                "median": round(sorted(pnls)[len(pnls)//2], 2),
                "worst": round(min(pnls), 2),
                "best": round(max(pnls), 2),
                "pct_profitable": round(sum(1 for p in pnls if p > 0)/len(pnls)*100, 1)}

    return {"chart_based": stats(chart_pnls), "fixed_pct": stats(fixed_pnls)}


if __name__ == "__main__":
    comp = compare_trailing_methods()
    print("--- Chart-based vs fixed trailing stop (500 trials) ---")
    for method, d in comp.items():
        print(f"  {method}: avg={d['avg']:+.1f}%, median={d['median']:+.1f}%, "
              f"worst={d['worst']:+.1f}%, best={d['best']:+.1f}%, win={d['pct_profitable']}%")
