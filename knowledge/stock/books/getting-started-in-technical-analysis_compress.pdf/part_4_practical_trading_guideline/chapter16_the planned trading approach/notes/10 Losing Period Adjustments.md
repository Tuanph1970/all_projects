# 10 Losing Period Adjustments

**Element 7 of [[03 Risk Control Plan]]** · [[00 Chapter 16 Index]]

## Definition

When a **discretionary trader** hits a sustained losing streak, the rule is: **cut size**, sometimes all the way to paper trading, until performance recovers. The drawdown signals that something is off — the trader's read of the market, their emotional state, or the edge itself — and the only way to find out without going broke is to reduce the bet.

**Important exception:** this rule does **not** apply to mechanical system traders. For a tested system, a losing period is mathematically expected and often *enhances* the probability of a recovery (mean-reverting equity, regression-to-system). Cutting size during a system drawdown can lock in losses that the system was about to claw back.

So the rule splits cleanly:

- **Discretionary trader** → losing streak = warning siren → reduce size or stop.
- **System trader** → losing streak = expected sample variance → keep sizing constant per the system rules.

## Easy Analogy

A discretionary trader is like a chef cooking by taste. If three diners in a row send the soup back, the chef should stop serving and figure out what changed — maybe the salt, maybe the palate, maybe the diners. Continuing to ladle out full bowls only multiplies the complaints.

A system trader is like a vending machine. If three customers in a row complain the snack was stale, the machine doesn't get to "reduce its output". The supplier checks the inventory cycle on schedule — sample variance is part of the contract.

## Numeric / Concrete Example

A discretionary swing trader normally risks 2% per trade on $100,000 = **$2,000 per trade**. Over six weeks they take eight trades and lose seven, drawing down to $86,000.

| Phase | Equity | Action |
|-------|--------|--------|
| Start | $100,000 | Normal sizing — $2,000/trade |
| After -14% drawdown | $86,000 | **Cut risk to 1%** → $860/trade |
| After +5% recovery | $90,300 | Stay reduced; require two more winners |
| Sustained recovery to $95k | $95,000 | Restore normal 2% sizing |
| Drawdown continues to -25% | $75,000 | **Stop trading**, paper-trade, review diary |

The cut is not a punishment — it is a fact-finding posture. Smaller size buys time to diagnose the problem without compounding it.

## Python Code

```python
def discretionary_size_factor(peak_equity, current_equity):
    """Scale-down factor based on % drawdown from peak. 1.0 = normal sizing."""
    dd = (peak_equity - current_equity) / peak_equity
    if dd < 0.05:   return 1.0      # noise
    if dd < 0.10:   return 0.75     # caution
    if dd < 0.20:   return 0.50     # half size
    return 0.0                       # stop trading, review

# After losing 14% from a $100k peak
discretionary_size_factor(100_000, 86_000)  # → 0.5
```

For system traders the equivalent function would simply `return 1.0` — no override.

## Relationships

### Within Chapter 16
- Often confused with [[09 Adjusting Leverage to Equity]], but they are distinct: equity adjustment is a **continuous mathematical** rescaling that applies to everyone; this rule is a **discrete psychological** intervention that applies only to discretionary traders.
- The diagnostic input is the [[16 Equity Chart]] — a sustained downward slope after an extended climb is exactly the trigger this rule responds to.
- The diagnosis itself is done with [[15 Segmented Trade Analysis]] — *which* segment is bleeding tells you what to fix.

### Outside Chapter 16
- **Chapter 14 — System Design** — explicitly warns against discretionary overrides of mechanical systems, which is why this rule excludes system traders.
- **Chapter 18 — Trader Wisdom** — multiple Market Wizards cite "stop trading when you're losing" as a survival rule, not a tactical one.

## When This Concept Works Well
- When the trader can honestly distinguish "I'm losing because the market is wrong for my style this month" from "I'm losing because I'm forcing trades". Both call for the cut, but the second is the one that takes traders out of the game permanently.
- When paper-trading at zero size during the cut phase keeps the trader engaged and producing data without bleeding capital.

## When It Fails
- When applied to a tested mechanical system — kills the recovery the system mathematically expects.
- When the trader uses "I'll cut size when I'm losing" as an excuse to keep trading at all, instead of stopping outright when the drawdown crosses the deep zone.
- When the cut is asymmetric (cut after losses, but never restored after recovery) — the trader's lifetime returns slowly compress to nothing.
