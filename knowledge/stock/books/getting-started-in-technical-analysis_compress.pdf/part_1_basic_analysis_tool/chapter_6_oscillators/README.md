# Chapter 6 — Oscillators (Obsidian Vault)

Source: Schwager, Jack D. — *Getting Started in Technical Analysis*, Chapter 6 (pp. 110–119).

This folder is structured as a self-contained Obsidian vault. Open the parent folder in Obsidian and the wiki-links between notes, images, and Python files will resolve automatically.

## Folder layout

```
chapter6/
├── README.md                  ← this file
├── Notes/                     ← Obsidian markdown notes (open these)
│   ├── 01_Chapter_6_Index.md  ← START HERE
│   ├── 02_Momentum.md
│   ├── 03_Rate_of_Change.md
│   ├── 04_Equilibrium_Line.md
│   ├── 05_Sensitivity.md
│   ├── 06_MA_Oscillator.md
│   ├── 07_Price_Oscillator.md
│   ├── 08_MACD.md
│   ├── 09_Overbought_Oversold.md
│   ├── 10_Normalized_Unbounded.md
│   ├── 11_RSI.md
│   ├── 12_Stochastics.md
│   ├── 13_Divergence.md
│   └── 14_Trading_Alerts.md
├── Images/                    ← chart illustrations (auto-embedded in notes)
│   ├── 01_momentum.png
│   ├── 02_roc.png
│   ├── 03_equilibrium_line.png
│   ├── 04_ma_oscillator.png
│   ├── 05_price_oscillator.png
│   ├── 06_macd.png
│   ├── 07_overbought_oversold.png
│   ├── 08_rsi.png
│   ├── 09_stochastics.png
│   ├── 10_divergence.png
│   ├── 11_trading_alerts.png
│   └── 12_sensitivity.png
└── Code/                      ← reference implementations
    ├── oscillators_master.py  ← all formulas
    └── generate_images.py     ← regenerates the chart panel
```

## Concept matrix (quick lookup)

| # | Concept | Note | Chart | Key formula |
|---|---------|------|-------|-------------|
| 1 | Momentum | [[02_Momentum]] | `01_momentum.png` | `Cₜ − Cₜ₋ₙ` |
| 2 | Rate of Change | [[03_Rate_of_Change]] | `02_roc.png` | `Cₜ / Cₜ₋ₙ` |
| 3 | Equilibrium Line | [[04_Equilibrium_Line]] | `03_equilibrium_line.png` | depends on oscillator |
| 4 | Sensitivity (n) | [[05_Sensitivity]] | `12_sensitivity.png` | look-back parameter |
| 5 | MA Oscillator | [[06_MA_Oscillator]] | `04_ma_oscillator.png` | `Cₜ − MAₙ` |
| 6 | Price Oscillator | [[07_Price_Oscillator]] | `05_price_oscillator.png` | `MA_short − MA_long` |
| 7 | MACD | [[08_MACD]] | `06_macd.png` | `EMA12 − EMA26`, signal `EMA9` |
| 8 | Overbought / Oversold | [[09_Overbought_Oversold]] | `07_overbought_oversold.png` | quantile / fixed level |
| 9 | Normalized vs Unbounded | [[10_Normalized_Unbounded]] | (concept) | bounded [0,100] vs free |
| 10 | RSI | [[11_RSI]] | `08_rsi.png` | `100 − 100/(1 + RS)` |
| 11 | Stochastics | [[12_Stochastics]] | `09_stochastics.png` | `(C − Lₙ) / (Hₙ − Lₙ) × 100` |
| 12 | Divergence | [[13_Divergence]] | `10_divergence.png` | pivot mismatch |
| 13 | Trading Alerts | [[14_Trading_Alerts]] | `11_trading_alerts.png` | alert + price confirm |

## How to use this vault

1. Open `Notes/01_Chapter_6_Index.md` in Obsidian → it links to all concept notes.
2. Each concept note follows the same template:
   - Definition (with formula)
   - Embedded chart from `Images/`
   - Common-life analogy
   - Worked numeric example
   - Python implementation snippet (links to `Code/oscillators_master.py`)
   - Within-chapter relationships
   - Cross-chapter relationships
   - Decision rule for when to use it
3. To regenerate the charts after editing formulas:
   ```bash
   cd Code
   pip install pandas numpy matplotlib
   python generate_images.py
   ```

## Reading order suggestion

For someone new to oscillators:

`Index → Momentum → ROC → Equilibrium Line → Sensitivity → MA Oscillator → Price Oscillator → MACD → Overbought/Oversold → Normalized vs Unbounded → RSI → Stochastics → Divergence → Trading Alerts`

The chapter builds inductively — every later concept reuses ideas from earlier ones, and the final note (Trading Alerts) is the practical synthesis Schwager recommends as the actual takeaway.

## Chapter takeaway in one sentence

> Oscillators are countertrend tools that work brilliantly in trading ranges and fail badly in trends; the prudent use is to treat their signals as **alerts** that need price confirmation before any trade is taken.
