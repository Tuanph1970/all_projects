# Trend Line Rules

## Description

Schwager's three conventional trading rules for trend lines and channels (pp.34-35). These form the basic decision framework for trading within a trend — when to enter, when to exit on reversal, and when to take profits.

## Simple Analogy

Think of a bus route. **Rule 1:** Board the bus when it returns to your stop (approach to trend line = entry). **Rule 2:** Get off immediately if the bus leaves its normal route (penetration = reversal). **Rule 3:** Plan your destination — don't ride to the end of the line when you can exit at a convenient stop (channel boundary = profit-taking zone).

## The Three Rules

### Rule 1: Approach = Entry Opportunity

> "Declines approaching an uptrend line and rallies approaching a downtrend line are often good opportunities to initiate positions in the direction of the major trend."

**Why it works:** Entry near the trend line means small stop distance (just beyond the line = defined risk) and large distance to the [[06 - Trend Channels|channel line]] (potential reward). The trend provides the directional edge; the line provides the risk structure.

### Rule 2: Penetration = Reversal Signal

> "The penetration of an uptrend line is a sell signal; the penetration of a downtrend line is a buy signal. Normally, a minimum percentage price move or a minimum number of closes beyond the trend line is required to confirm a penetration."

**Three confirmation methods** (from Ch.7 and Ch.14):
1. **Percentage penetration** — price must close ≥X% beyond the line (e.g., 2%)
2. **Multiple closes** — N consecutive closes beyond the line (e.g., 3)
3. **Time delay** — wait N days, recheck if still beyond (e.g., 6 days)

**Critical caveat:** Schwager warns that trend line penetrations are "more the rule than the exception" — see [[11 - False Penetrations]]. This is why Chapter 11's failed signals become more reliable than the signals themselves.

### Rule 3: Channel Line = Profit-Taking Zone

> "The lower end of a downtrend channel and the upper end of an uptrend channel represent potential profit-taking zones for short-term traders."

**Key distinction:** The channel line is NOT a reversal signal. It means "the easy money in this swing is done" — not "the trend is over." Short-term traders exit; long-term holders may keep positions with trailing stops.

## Illustration

**Charts:**
- `assets/charts/rule1_entry_at_trendline.png` — Entry at support/resistance with risk/reward
- `assets/charts/rule2_penetration_signal.png` — Confirmation methods and confirmed vs false breaks
- `assets/charts/rule3_channel_profit_taking.png` — Profit-taking at channel boundaries
- `assets/charts/rules_combined.png` — All three rules working together in one trading cycle

## Python Code

**File:** `assets/code/trend_line_rules_illustrations.py` — Generates all four illustration charts

## Connections

- **Depends on:** [[03 - Conventional Trend Lines]], [[06 - Trend Channels]]
- **Rule 2 leads to:** [[11 - False Penetrations]] (when penetrations fail), Ch.11 Failed Signals
- **Rule 3 relates to:** Ch.10 Setting Objectives and Position Exit Criteria
- **Stop placement:** Ch.9 — trend line as stop reference (Rule 1 risk definition)
- **Source:** Schwager pp.34-35

---
*Tags: #trading-rules #schwager-ch3 #decision-framework*
