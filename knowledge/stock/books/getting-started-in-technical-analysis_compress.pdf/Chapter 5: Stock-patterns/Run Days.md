---
tags: [technical-analysis, schwager, one-day-pattern, run-days, appendix]
source: "Schwager - Getting Started in Technical Analysis, Appendix pp.317-319"
related: ["[[One-Day Patterns MOC]]", "[[Thrust Days]]", "[[True Range and ADTR]]"]
---

# Run Days

## Definition

A run day is a strongly trending day that dominates its neighborhood in **both directions** — looking backward AND forward. Defined in Schwager's Appendix using [[True Range and ADTR|true high/low]]:

### Up Run Day (N = 5)
1. True high of the day > maximum true high of the **past** N days
2. True low of the day < minimum true low of the **next** N days

### Down Run Day (N = 5)
1. True low of the day < minimum true low of the **past** N days
2. True high of the day > maximum true high of the **next** N days

## Analogy

If a [[Thrust Days|thrust day]] is winning a single game, a run day is winning so dominantly that nobody beats your score for the next week either. You're not just ahead today — you've set a benchmark that holds up in both directions.

Clusters of run days are like a team on a winning streak — evidence of a **regime**, not a fluke.

## Critical Limitation

⚠️ **Run days cannot be identified in real time.** Condition 2 requires N future bars. This makes them useful for:
- **Historical regime analysis** — "this period was a trending phase"
- **Backtesting** — labeling market regimes after the fact
- **Confirmation** — recognizing in hindsight that a cluster of run days validates a trend thesis

They are NOT useful as trade entry signals.

## Relationship to Thrust Days

> Essentially, a run day is a more powerful version of a thrust day, although it is possible for a run day to fail to meet the thrust day condition.

Most run days are also thrust days, but the reverse is not true. Interestingly, Schwager notes it's possible for a run day to NOT be a thrust day — a day's low could be below the past 5-day low while its high is above the next 5-day high, yet the close could be above the previous day's low (failing the downthrust condition).

## Clustering as Regime Evidence

- **Clusters of up run days** → evidence the market is in a bullish phase
- **Clusters of down run days** → evidence the market is in a bearish state
- The name "run day" comes from the fact they tend to occur when the market is in a "trend run"

## Python Detection

```python
def detect_run_days(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    IMPORTANT: Requires N future bars — historical analysis only.
    """
    prev_close = df['close'].shift(1)
    true_high = pd.concat([df['high'], prev_close], axis=1).max(axis=1)
    true_low  = pd.concat([df['low'],  prev_close], axis=1).min(axis=1)

    results = []
    for i in range(n, len(df) - n):
        th = true_high.iloc[i]
        tl = true_low.iloc[i]
        past_th_max    = true_high.iloc[i-n:i].max()
        past_tl_min    = true_low.iloc[i-n:i].min()
        future_th_max  = true_high.iloc[i+1:i+1+n].max()
        future_tl_min  = true_low.iloc[i+1:i+1+n].min()

        if th > past_th_max and tl < future_tl_min:
            results.append({'date': df.index[i], 'type': 'up_run'})
        if tl < past_tl_min and th > future_th_max:
            results.append({'date': df.index[i], 'type': 'down_run'})

    return pd.DataFrame(results)
```
