# 12 Traders Notebook

**Step 5 of the [[00 Chapter 16 Index|Planned Trading Approach]]**

![[10_traders_notebook.svg]]

## Definition

The **trader's notebook** is a structured spreadsheet — one row per trade, fixed columns — that captures every fact about every trade *before, during, and after* it is closed. Schwager specifies a 17-column layout grouped into four blocks:

1. **Identification** — trade #, market, position (long/short), # of contracts/shares.
2. **Entry plan** — entry date, planned entry price, actual fill, planned objective, initial stop.
3. **In-flight management** — current stop (only ever tightened, never widened), notes.
4. **Exit & P&L** — exit date, exit price, gross P&L, commissions/slippage, net P&L, **implied risk** at entry.

The most underrated column is **implied risk** — the dollar amount that would have been lost if the initial stop had hit. Summing this across all open positions gives the **cumulative risk exposure**, and Schwager's rule of thumb is that this sum should not exceed roughly **25–35% of total equity** at any time.

The notebook is also the right place to log **paper trades** — they cost nothing and produce data that's nearly as good as live data for evaluating an edge.

## Easy Analogy

A pilot's flight log. The log records every flight — fuel on board, route, weather, takeoff time, landing time, anomalies. No pilot writes the log "when something interesting happens"; they write every entry, every flight, including the boring ones. Boring flights are how a pilot proves the procedures still work; boring trades are how a trader proves the edge still exists.

## Numeric / Concrete Example

A trader has three open positions on a $100,000 account:

| Trade | Market | Size | Entry | Stop | Implied Risk |
|-------|--------|------|-------|------|--------------|
| #41 | AAPL | 200 | $175 | $168 | **$1,400** |
| #42 | XOM | 300 | $108 | $103 | **$1,500** |
| #43 | GLD long | 50 | $182 | $176 | **$300** |

**Cumulative implied risk = $3,200 = 3.2% of equity.** Well inside the 25–35% ceiling — there is room for 6–8 more concurrent positions of similar size before the rule would refuse a new entry.

After trade #41 closes: AAPL stops out at $168.10 (slippage $0.10/share). The notebook row gets completed:

| Exit Date | Exit | Gross P&L | Commission | Net P&L | Notes |
|-----------|------|-----------|------------|---------|-------|
| 2026-04-22 | $168.10 | -$1,380 | -$2 | **-$1,382** | Stop hit on sector pullback; slippage minimal. |

Notice the loss is **smaller than the implied risk** thanks to favourable slippage. Recording both numbers separately lets the trader later compute average slippage and check whether their backtested results are realistic.

## Python Code

The full implementation is [[03_traders_notebook.py]]. Key methods:

```python
nb = TraderNotebook(equity=100_000, csv_path='trades.csv')

# At entry — refuses if cumulative risk would exceed cap
nb.open_trade(market='AAPL', direction='long', size=200,
              entry_price=175, stop_price=168, objective=195)

# During trade — refuses if new stop is worse than current
nb.update_stop(trade_id=41, new_stop=171)

# At exit — auto-computes net P&L and persists CSV
nb.close_trade(trade_id=41, exit_price=168.10, commission=2)

print(nb.cumulative_risk_pct())   # → 1.8% (after closing #41)
```

The class enforces three rules in code, not in willpower:
1. **No widening stops** ([[05 Stop-Loss Strategy]]).
2. **Cumulative risk cap** ([[04 Maximum Risk Per Trade]]).
3. **Mandatory fields** at entry — no trade can be opened with a missing stop.

## Relationships

### Within Chapter 16
- **The data backbone of the chapter.** Every other rule produces or consumes notebook columns:
    - [[04 Maximum Risk Per Trade]] sets the implied-risk cap.
    - [[05 Stop-Loss Strategy]] populates the stop columns.
    - [[09 Adjusting Leverage to Equity]] reads the equity field to size new entries.
    - [[15 Segmented Trade Analysis]] is impossible without the data this notebook captures.
- Filled in nightly during [[11 Planning Time Routine]]; the qualitative companion is [[13 Traders Diary]].

### Outside Chapter 16
- **Chapter 15 — Testing Systems** — the notebook is the live counterpart to the test database. The same data structure that came out of backtesting now comes out of real trading, and they should be comparable.
- **Chapter 18 — Rule #10 (Trading Plan)** — the plan exists on paper precisely so it can be matched against the notebook record at the end of each week.

## When This Concept Works Well
- When **every trade** is recorded — including paper trades, scratched trades, and "I just had a feeling" trades. Selective recording produces selective conclusions.
- When the cumulative-risk column is summed daily and shown at the top of the spreadsheet, where it is impossible to ignore.

## When It Fails
- When the trader keeps the notebook in their head ("I remember every trade") — memory is biased toward winners.
- When losing trades' diary entries are sparse and winners are essays. The lessons are in the losers.
- When the notebook becomes a transcription chore done weekly in a single rushed session — by then the entry rationale has already been lost.
