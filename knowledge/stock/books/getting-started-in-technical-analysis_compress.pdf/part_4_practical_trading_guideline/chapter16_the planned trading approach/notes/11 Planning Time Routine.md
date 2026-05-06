# 11 Planning Time Routine

**Step 4 of the [[00 Chapter 16 Index|Planned Trading Approach]]**

![[09_planning_routine.svg]]

## Definition

A **fixed daily block of time** — typically 30 to 60 minutes after the close — dedicated to three tasks:

1. **Update systems and charts.** Recompute indicators, redraw trendlines, run any scheduled scans against the day's closing prices.
2. **Plan new trades.** Identify setups that may trigger tomorrow; pre-decide entry, stop, and size for each.
3. **Update exit points on open positions.** Move stops, refresh objectives, and review whether anything has changed enough to scratch the trade tomorrow.

The point is not the specific tasks — it's that **decisions get made when markets are closed**, when there is no price ticking and no money on the line. Decisions made during the trading day are reactions; decisions made the night before are plans.

There's one explicit guardrail on Task 3: **stop adjustments may only reduce risk, never increase it**. Widening a stop in the evening is the same self-deception as widening one mid-day — it just has nicer lighting.

## Easy Analogy

A pilot's preflight checklist. The plane is on the ground, the engines are off, the pilot is calm — perfect conditions for noticing a deflated tire. Doing the same check at 30,000 feet during turbulence is impossible; doing it before takeoff is routine. Markets close so traders can run their checklist.

## Numeric / Concrete Example

A swing trader closes their day-job laptop at 6 pm, makes coffee, and spends 45 minutes:

| Time | Task | Output |
|------|------|--------|
| 6:00–6:15 | Update charts on 12 watchlist stocks | 3 stocks now in setup zones |
| 6:15–6:35 | Plan tomorrow's potential entries | 2 trades pre-staged with entry, stop, size in [[12 Traders Notebook]] |
| 6:35–6:45 | Review 4 open positions | 1 trailing stop tightened from $48 to $51 (long); no other changes |

Total: 45 minutes. Tomorrow morning they place GTC orders before the open and walk away — no live decisions required.

Compare to the trader without a routine: at 9:42 am tomorrow they spot the setup, fumble for stop placement, eyeball position size, and realise at 10:15 they got filled at a worse price than they would have committed to last night.

## Python Code

```python
from datetime import datetime, time

def in_planning_window(now=None, start=time(18, 0), end=time(19, 0)):
    """Reminder helper: am I inside my planning hour?"""
    now = now or datetime.now().time()
    return start <= now <= end

def update_stop(direction, current_stop, candidate_stop):
    """ENFORCED: stop can only move in the favourable direction."""
    if direction == 'long':
        return max(current_stop, candidate_stop)   # never lower
    return min(current_stop, candidate_stop)       # never raise
```

The `update_stop` helper is also used in [[03_traders_notebook.py]]; the same one-way rule is enforced there.

## Relationships

### Within Chapter 16
- This routine is when [[12 Traders Notebook]] gets filled in, when [[13 Traders Diary]] entries are written, and when [[16 Equity Chart]] is updated.
- Pre-deciding entry, stop, and size in advance is the practical mechanism that makes [[04 Maximum Risk Per Trade]] and [[05 Stop-Loss Strategy]] actually happen — both rules collapse if size and stop are improvised at the moment of entry.
- A weekly version of this routine is when the trader runs [[15 Segmented Trade Analysis]] and reviews the [[16 Equity Chart]].

### Outside Chapter 16
- **Chapter 18 — Rule #11 (Discipline)** — many of the interviewed traders describe an after-hours preparation ritual as the single habit that distinguished their profitable years from their losing ones.

## When This Concept Works Well
- When the routine happens at the same time every day, regardless of whether trades are open. Skipping "because nothing happened today" is exactly when undisciplined drift starts.
- When the trader treats it as protected time — phone face-down, no other tabs.

## When It Fails
- When the trader skips the routine on winning days ("on a roll, no need to overthink") — these are the days that quietly set up tomorrow's overconfidence trade.
- When stop adjustments during the routine drift toward "giving the trade more room". The widen-the-stop temptation is more dangerous in the evening than in real time, because the trader has had hours to construct rationalisations.
- When planning-time analysis becomes endless screen time. The 30–60 minute box is a feature, not a constraint.
