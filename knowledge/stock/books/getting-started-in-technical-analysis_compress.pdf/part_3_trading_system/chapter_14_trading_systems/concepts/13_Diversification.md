# 13 — Diversification (Markets, Systems, and SMSVs)

## Definition

The standard meaning of **diversification** is "spread your trading across many markets so that adverse moves in one market are offset by neutral or favorable moves elsewhere." Schwager extends this definition along **three orthogonal axes**:

1. **Multiple markets.** The classic dimension. If gold and soybeans are imperfectly correlated, a drawdown in both at the same time is much less likely than a drawdown in either alone.

2. **Multiple systems per market.** A single instrument can be traded by a trend-follower *and* a countertrend strategy *and* a pattern-recognition system, each catching different market regimes.

3. **Multiple parameter sets per system per market.** Instead of betting that *N=20* is the magic breakout length, run *N=10*, *N=20*, and *N=40* simultaneously, each with a fractional unit size.

The chapter introduces the **Single Market System Variation (SMSV)** as the atomic unit: one specific (market, system, parameter set) combination. A real portfolio is a collection of SMSVs.

Two benefits beyond the obvious drawdown reduction:

- **Insurance against missing the rare giant moves.** A single market can sit dormant for years while another quietly delivers the move that defines the year.
- **Smoother equity curves enable more leverage.** A diversified portfolio with the same per-trade risk-of-ruin can support a higher overall position size — diversification doesn't just reduce risk, it raises the ceiling on return.

## Illustration

![[13_diversification.png]]

Left: equity curves of a single market (red) vs. an equal-weighted six-market portfolio (green). The single market drifts down with deep retracements; the diversified portfolio is smoother and ends higher. Right: drawdowns. Single market reaches –33%; the portfolio caps near –10%. Same return components, dramatically different ride.

## Analogy

You make a living mowing lawns. You can:

- Mow only one lawn (one big customer). When that customer goes on vacation, your income hits zero.
- Mow lawns for ten customers across town. When any one is on vacation, the other nine still need mowing. Your income stream is far less volatile.
- Mow lawns for ten customers *and* shovel snow in winter (multiple systems). Now you're not even dependent on the same season.
- Within mowing, charge a flat rate for some customers and per-square-foot for others (multiple parameter sets). Different rate structures behave differently in different conditions.

The smoother your income, the more confidently you can take on a mortgage (= leverage).

## Numeric example

```
Single market : final equity 0.721, max drawdown –33.15%
6-market port : final equity 1.079, max drawdown –10.50%
```

Same per-market profile, six imperfectly correlated markets, equal-weighted. The drawdown collapses by roughly two-thirds. The final equity also happens to be higher in this run — because deeper drawdowns compound *negatively* against the portfolio in a way diversification avoids.

The classic textbook calculation: if each of two uncorrelated markets has a $3,000 average drawdown on a $20,000 account, trading both contracts simultaneously rarely produces the simple sum ($6,000) drawdown — because the drawdowns aren't synchronized. Only perfectly correlated markets would yield the worst case.

## Code

[[../codes/13_diversification.py]]

```python
def max_drawdown(equity):
    peak = np.maximum.accumulate(equity)
    return ((equity - peak) / peak).min()

def simulate_market(seed, n=250, mu=0.0006, sigma=0.018):
    rng = np.random.default_rng(seed)
    rets = rng.normal(mu, sigma, n)
    return np.cumprod(1 + rets)

# Single market vs equal-weighted 6-market portfolio
markets = [simulate_market(seed=s) for s in [1, 2, 3, 4, 5, 6]]
log_rets = np.column_stack([np.diff(np.log(m)) for m in markets])
portfolio_eq = np.cumprod(1 + log_rets.mean(axis=1))
```

## Relationships

### Within the chapter

- **Complements every other concept in the chapter.** Diversification is what makes the entire trend-following framework viable in practice — a single market with a single system has too much variance to trade with confidence.
- **Pairs especially well with:** [[12_Countertrend_Systems]] (mixing trend and countertrend systems is one of the strongest forms of diversification — they thrive in opposite regimes).
- **Reduces the risk of overfitting:** Schwager argues that trading several reasonable parameter sets is more robust than trading one "optimal" set, because optimization is largely an illusion ([[00_Chapter14_Overview]] section "Schwager's 10 problems").

### Beyond the chapter

- **Ch. 15 (Testing & Optimization):** the explicit recommendation to use *blind simulation* and *average parameter set performance* — a direct echo of axis #3.
- **Ch. 16 (Planned Trading Approach):** chapter 16 walks through portfolio construction with explicit attention to *correlated markets* (e.g., a basket of currency futures is *not* truly six-market diversification — they're highly correlated).
- **Ch. 17 (82 Trading Rules):** several rules pertain to position sizing across the portfolio.
- **Modern portfolio theory (outside the book):** the Markowitz formalism is the mathematical scaffolding behind these intuitions.

### When does diversification help most?

- **Portfolios of imperfectly correlated assets.** Highly correlated markets (six tech stocks, six currencies) provide much weaker diversification than the surface market count suggests.
- **Long-horizon trading.** The benefits of diversification compound over time; on a single trade, only the per-trade variance matters.
- **When trading capital permits enough granularity.** You need enough capital to trade fractional units of each SMSV — $50,000 across 30 SMSVs is meaningless granularity.

It can hurt when:
- **All markets enter a correlated crisis** (2008, March 2020). Correlations go to 1 exactly when you need diversification most.
- **Diversification is illusory** — six tech stocks behave like one position during a tech selloff.
- **Operational complexity overwhelms execution quality** — too many SMSVs to monitor leads to errors.
