# Chapter 9 — Choosing Stop-Loss Points (Obsidian Vault)

This vault contains my study notes for **Chapter 9** of *Getting Started in Technical Analysis* by Jack D. Schwager.

## 📁 Folder layout

```
chapter09/
├── index/
│   ├── Chapter 09 - Choosing Stop-Loss Points.md   ← Map of Content (start here)
│   └── Chapter 09 - Relationship Map.md             ← How the concepts connect
├── concepts/                                        ← One markdown note per concept
│   ├── Stop-Loss Liquidation Point.md
│   ├── GTC Stop Order.md
│   ├── Trend Line Stop.md
│   ├── Trading Range Stop.md
│   ├── Flag and Pennant Stop.md
│   ├── Wide-Ranging Day Stop.md
│   ├── Relative High Low Stop.md
│   ├── Money Stop.md
│   ├── Trailing Stop.md
│   └── CIC Anti-Pattern.md
├── images/                                          ← SVG illustrations (one per concept)
│   ├── stop_loss_liquidation_point.svg
│   ├── gtc_stop_order.svg
│   ├── trend_line_stop.svg
│   ├── trading_range_stop.svg
│   ├── flag_pennant_stop.svg
│   ├── wide_ranging_day_stop.svg
│   ├── relative_high_low_stop.svg
│   ├── money_stop.svg
│   ├── trailing_stop.svg
│   └── cic_anti_pattern.svg
└── code/                                            ← Runnable Python modules
    ├── 01_stop_loss_liquidation_point.py
    ├── 02_gtc_stop_order.py
    ├── 03_trend_line_stop.py
    ├── 04_trading_range_stop.py
    ├── 05_flag_pennant_stop.py
    ├── 06_wide_ranging_day_stop.py
    ├── 07_relative_high_low_stop.py
    ├── 08_money_stop.py
    ├── 09_trailing_stop.py
    └── 10_cic_anti_pattern.py
```

## 🚀 How to use in Obsidian

1. **Open the folder as a vault**: `File → Open folder as vault → chapter09/`
2. **Start at**: `index/Chapter 09 - Choosing Stop-Loss Points.md`
3. Wikilinks like `[[GTC Stop Order]]` and embeds like `![[trend_line_stop.svg]]` will resolve automatically as long as Obsidian's *"Use [[wikilinks]]"* and *"Detect all file extensions"* are enabled.

> Tip: turn on **Settings → Files & Links → Default location for new attachments → "Same folder as current file"** if you plan to add screenshots later.

## 🐍 Run the code

```bash
cd code/
python3 01_stop_loss_liquidation_point.py    # any of the 10 modules
```

Only `03_trend_line_stop.py` requires `numpy`. Everything else is pure stdlib.

## ✅ What each note contains

Per the study template:

- **Definition** — concise restatement of the concept
- **Illustration** — embedded SVG (in `images/`)
- **Simple analogy** — everyday-life metaphor
- **Numeric example** — worked-out numbers
- **Python code** — same code as the corresponding `code/*.py` file
- **Within-chapter relationships** — when this concept works well; comparisons to siblings
- **Cross-chapter relationships** — links forward and backward in the book
- **Key takeaway** — one-sentence summary
