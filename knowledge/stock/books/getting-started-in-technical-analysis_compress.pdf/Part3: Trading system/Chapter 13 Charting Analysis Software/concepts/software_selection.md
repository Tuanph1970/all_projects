# Software Selection Framework
**Chapter:** [[Chapter_13_Index|13 — Charting and Analysis Software]]  
**Source:** Schwager, *Getting Started in Technical Analysis*, p.223–225

---

## Definition
The software selection framework is Schwager's **three-factor decision model** for choosing the right charting or analysis software before purchase. The three factors are: **(1) Time Frame / Trading Style**, **(2) Analytical Goals**, and **(3) Computer Skills**. The key principle is to pay only for features you will actually use — more expensive does not mean more suitable.

---

## Simple Analogy
Choosing charting software is like **buying a camera**. A beginner photographer needs a good smartphone camera — cheap, automatic, easy. A portrait photographer needs a mid-range DSLR with interchangeable lenses. A wildlife filmmaker needs a $15,000 professional rig with zoom lenses and weather sealing. Buying the filmmaker's rig when you just want to post photos on social media is wasteful and overwhelming. Match the tool to the job.

---

## Chart Illustration
![[charts/software_selection.png]]
*Left: three software tiers with features, user type, and data type. Right: decision matrix mapping your time frame, goals, skills, and budget to the appropriate tier.*

---

## Real Numeric Example
| Software Tier | Price | Data Type Needed | Monthly Data Cost | Year 1 Total |
|--------------|-------|-----------------|-------------------|--------------|
| Entry-Level | $50–$100 (once) | Historical only | $0–$10 | ~$100–$220 |
| Mid-Level | $200–$500 (once) | Historical + EOD | $15–$50/mo | ~$380–$1,100 |
| Advanced | $500–$3,000 (once) | Real-time + EOD | $200–$500/mo | ~$2,900–$9,000 |

**Note:** Many vendors let you upgrade at a discount — start low, move up when genuinely needed.

---

## Python Code
**File:** [[code/software_selection.py]]
```python
# Key snippet — Decision matrix scoring
import numpy as np

# Rows = software tiers, Cols = [TimeFrame, AnalyticalGoals, ComputerSkills, Budget]
# Score: 1=basic, 2=medium, 3=advanced requirement
scores = np.array([
    [1, 1, 1, 1],   # Entry-Level
    [1, 2, 2, 2],   # Mid-Level
    [3, 3, 3, 3],   # Advanced
])

def recommend_tier(intraday: bool, wants_backtesting: bool,
                    can_code: bool, budget_usd: int) -> str:
    score = (3 if intraday else 1) + (2 if wants_backtesting else 1) + \
            (2 if can_code else 1) + (3 if budget_usd > 1000 else
                                       2 if budget_usd > 300 else 1)
    if score >= 10: return "Advanced"
    if score >= 6:  return "Mid-Level"
    return "Entry-Level"

print(recommend_tier(False, True, False, 400))  # → Mid-Level
```

---

## Relationships

### Within Chapter 13
| Concept | How They Relate |
|---------|-----------------|
| [[Historical Price Data]] | Entry-level software often bundles historical data; your data choice constrains software |
| [[End-of-Day Price Data]] | Mid-level software must have price *download* capability to use EOD |
| [[Real-Time (Tick) Price Data]] | Only advanced/specialised software handles real-time feeds |
| [[Data Quality and Cleaning]] | Better software automates error detection; cheaper software may not |
| [[Continuous Futures Data]] | Advanced software handles continuous futures construction automatically |

### Outside Chapter 13
| Chapter | Concept | Relationship |
|---------|---------|--------------|
| Ch. 14 | Trading System Design | System design requires mid-to-advanced software with programming capability |
| Ch. 15 | System Testing | Robust testing (optimisation, walk-forward) requires advanced software |
| Ch. 6 | Oscillators | Standard oscillators (RSI, MACD) come pre-built even in mid-level software |

### Analytical Programs vs. Trading Programs (Schwager's Distinction)
| Type | What It Does | Who Uses It |
|------|-------------|-------------|
| **Analytical program** | Lets YOU analyse and decide | Active technical analyst |
| **Trading program** | Generates buy/sell signals automatically | System trader |
| **Hybrid** | Both, but you're usually paying for the system | Be careful: know what you're buying |

---

## Tags
#software #charting #selection-framework #trading-tools #budget #technical-analysis #chapter13
