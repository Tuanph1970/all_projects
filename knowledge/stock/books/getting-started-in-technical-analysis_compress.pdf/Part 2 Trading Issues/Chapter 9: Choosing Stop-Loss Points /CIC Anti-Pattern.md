---
title: "CIC Anti-Pattern"
chapter: 9
concept_number: 9
tags:
  - technical-analysis
  - stop-loss
  - behavioral-risk
  - psychology
  - anti-pattern
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Trailing Stops]]"
  - "[[Risk Control and Win Rate vs Profitability]]"
  - "[[Money Stops]]"
  - "[[Confirmation Conditions]]"
created: 2026-04-09
---

# CIC Anti-Pattern

## Definition

**CIC = "Cancel If Close"** — the behavioral failure mode where a trader places a correct stop-loss order but cancels it when price approaches the stop level. This defeats the entire purpose of the stop and transforms a controlled, bounded loss into an unbounded catastrophe.

Schwager places this as the **closing statement** of Chapter 9 — the final word after teaching eight stop placement techniques. This positioning is deliberate: everything in the chapter is worthless if the trader cancels the stop when it matters.

**CIC is the only concept in this chapter that is never correct.** Every other stop type involves genuine tradeoffs. CIC has no tradeoff — it is purely destructive.

## Key Quotes (Schwager)

> "As a general rule, stops should only be changed in order to reduce risk."

> "Some traders who can't stand the thought of getting stopped out at the bottom of a move (or at the top if short) may be diligent in placing a GTC stop order upon initiating the position, but then cancel the order when the market gets within range."

> "This type of order has been derisively, albeit appropriately, referred to as a CIC (cancel if close) order."

> "Revising the stop to allow greater risk defeats the entire purpose of the stop."

The opening Lefèvre quote foreshadows the full CIC lifecycle:

> "They would not take a small loss at first but had held on, in the hope of a recovery that would 'let them out even.' And prices had sunk and sunk until the loss was so great that it seemed only proper to hold on, if need be a year, for sooner or later prices must come back. But the break 'shook them out,' and prices just went so much lower because so many people had to sell, whether they would or not."

## The Six-Stage Escalation Cycle

CIC follows a predictable psychological escalation:

| Stage | State | Psychology | SRE parallel |
|-------|-------|------------|-------------|
| 1. Setup | Stop placed correctly | Discipline intact | Monitoring configured with SLOs |
| 2. Approach | Price nears stop | Anxiety rises | Alert fires on threshold breach |
| 3. Override (CIC) | Stop canceled | Relief from anxiety | Alert threshold raised / silenced |
| 4. Growing loss | -5% → -15% | "Too late to sell now" | Latency crosses 2s, 5s unchecked |
| 5. Rationalization | -15% → -25% | "It'll come back" | "Can't restart — lose in-flight work" |
| 6. Catastrophe | -30%+ forced exit | Despair | Full system cascade |

Schwager bookends the chapter with this cycle: Lefèvre describes it narratively at the opening; CIC names it technically at the close.

## Analogy: Silencing Alerts During an Incident

The full SRE parallel, stage by stage:

1. **Deploy with proper monitoring** — alert thresholds derived from meaningful SLOs (= chart-based stop at technical level)
2. **Alert fires** — CPU 85%, latency P99 > 500ms. The alert is correct. (= Price approaches stop)
3. **Engineer raises threshold to 95%** — "probably transient" (= Cancel the stop)
4. **Underlying issue continues** — memory leak, connection pool exhaustion (= Loss grows unchecked)
5. **Can't restart now** — "we'd lose all in-flight transactions" (= "Loss too big to take")
6. **Full system cascade** — all in-flight transactions lost anyway, plus everything accumulated after silence (= Forced liquidation at the worst point)

Silencing the alert didn't fix the issue. It removed the mechanism that would have caught it early.

## The Intermittent Reinforcement Trap

CIC is especially dangerous because it is **intermittently reinforced** — it "works" most of the time:

- Many times you cancel a stop, price does recover, and you feel vindicated
- This creates variable-ratio reinforcement (the same psychology as slot machines and gambling addiction)
- The catastrophes are infrequent enough that the trader attributes them to "bad luck" rather than bad process
- But the catastrophic losses are so large that they overwhelm all the small wins

### Simulation evidence (20 trades at a time):

- CIC "wins" on **50-70% of individual trades** (price recovers after the stop would have fired)
- But 1-3 catastrophic losses (>20%) per 20 trades wipe out all the wins
- Cumulative CIC return almost always ends worse than disciplined, **despite winning the majority of trades**

This is the bait: CIC appears to work most of the time, which reinforces the behavior. The rare catastrophes are written off as exceptions rather than recognized as the structural outcome of removing the loss cap.

## Connection to Expected Value (Chapter 7)

The expected value formula from [[Risk Control and Win Rate vs Profitability]]:

```
E = (win_rate × avg_win) - ((1 - win_rate) × avg_loss)
```

CIC removes the cap on `avg_loss`. With a stop, `avg_loss` is bounded (e.g., 5%). Without a stop, `avg_loss` is unbounded — a single -90% loss makes the entire equation negative regardless of win rate.

You can have a 90% win rate and still go bankrupt if the 10% losses are unbounded. That is the mathematical statement of CIC's destructiveness.

## Backtest Results (1,000 trials, 5% initial stop)

| Metric | Disciplined | CIC (cancel and hold) |
|--------|------------|----------------------|
| Avg P&L | -4.4% | **-17.5%** |
| Median P&L | -6.0% | -17.6% |
| Worst case | **-15.9%** | **-90.0%** |
| 5th percentile | -9.3% | **-61.5%** |
| % losing trades | 91.8% | 73.4% |
| % catastrophic (>20% loss) | **0.0%** | **46.3%** |

Key insights:
- CIC worst case is **5.7x worse** (-90% vs -15.9%)
- **46.3%** of CIC trades become catastrophic vs **0%** disciplined
- CIC has *fewer* losing trades (73.4% vs 91.8%) — this is the bait that reinforces the behavior
- The gap between 73.4% and 91.8% losing trades is the "CIC works" illusion; the gap between 0% and 46.3% catastrophic is the reality

## Prevention Strategies

| Strategy | Mechanism | Software equivalent |
|----------|-----------|-------------------|
| GTC orders entered simultaneously with trade | Removes decision from runtime | Infra-as-code: thresholds deployed with the service |
| Automated execution (algo) | No emotions to override | Automated runbooks that can't be overridden |
| Pre-commitment (write down the stop) | Accountability through documentation | Incident response playbook written before the incident |
| Position sizing | If the loss amount is unbearable, position is too large | If the alert is too noisy, fix the threshold, don't silence it |
| Process review (track every canceled stop) | Data shows the pattern | Post-incident review of every silenced alert |

## When CIC Occurs (Risk Factors)

- **Every market condition** — CIC is behavioral, not market-dependent
- **Strong directional conviction** — "I know this stock is going up" overrides the stop
- **Volatile markets** — stops are approached more frequently, more opportunities to cancel
- **Wide stops** — the dollar amount feels larger, anxiety is greater
- **Winning streak** — overconfidence from recent wins makes the stop feel unnecessary
- **After a previous false stop** — "I got stopped out and it bounced — not again"

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — CIC violates Rule 3: "stops should only be changed in order to reduce risk." CIC is the anti-Rule-3.
- **[[Trailing Stops]]** (Ch. 9, Concept 8) — The correct direction to move stops: tighter, not wider. Every trailing stop raise is a one-way ratchet; CIC undoes the ratchet.
- **[[Risk Control and Win Rate vs Profitability]]** (Ch. 7) — CIC destroys expected value by removing the loss cap from the equation. Win rate becomes irrelevant if avg_loss is unbounded.
- **[[Money Stops]]** (Ch. 9, Concept 7) — Even a money stop (no technical basis) is infinitely better than a canceled stop. Any bounded risk > unbounded risk.
- **[[Confirmation Conditions]]** (Ch. 7) — If the problem is too many false stops, the correct solution is adding confirmation conditions (time delay, minimum penetration), NOT canceling the stop.

## Python Implementation

See `cic_anti_pattern.py`:

- `detect_cic_behavior()` — Flags any stop modification that increases risk, with warning message
- `simulate_cic_vs_discipline()` — 1,000-trial backtest comparing disciplined execution to CIC behavior, with percentile and catastrophic rate analysis

## Summary

CIC is the **behavioral gravity well** that all the other concepts in Chapter 9 exist to resist. It feels logical in the moment ("it'll come back"), it appears to work most of the time (intermittent reinforcement), and its catastrophic failures are rare enough to be attributed to bad luck. But the math is unambiguous: removing the loss cap makes the expected value equation undefined, and a single unbounded loss can destroy an account regardless of win rate. Schwager places CIC at the end of the chapter as a deliberate closing warning: **everything you've just learned about stop placement is worthless if you cancel the stop when it matters most.**
