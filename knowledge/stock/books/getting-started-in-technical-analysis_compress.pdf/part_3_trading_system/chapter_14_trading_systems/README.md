# Chapter 14 Knowledge Pack — Technical Trading Systems: Structure and Design

A complete Obsidian-ready study pack for *Getting Started in Technical Analysis* by Jack D. Schwager, **Chapter 14**.

## What's in here

```
ch14/
├── README.md                              ← you are here
├── concepts/
│   ├── 00_Chapter14_Overview.md          ← start here (concept map + index)
│   ├── 01_Trend_Following_Systems.md
│   ├── 02_Moving_Average_Systems.md
│   ├── 03_Weighted_Moving_Averages.md
│   ├── 04_Crossover_Moving_Average_System.md
│   ├── 05_Breakout_Systems.md
│   ├── 06_Confirmation_Conditions.md
│   ├── 07_Filter.md
│   ├── 08_Market_Characteristic_Adjustments.md
│   ├── 09_Buy_Sell_Differentiation.md
│   ├── 10_Pyramiding.md
│   ├── 11_Trade_Exit.md
│   ├── 12_Countertrend_Systems.md
│   └── 13_Diversification.md
├── images/                                ← 13 chart illustrations (PNG)
│   └── 01..13_*.png
└── codes/                                 ← 13 runnable Python scripts
    └── 01..13_*.py
```

## How each note is structured

Every concept note follows the same template, designed for fast reference:

1. **Definition** — what the concept is, plainly stated.
2. **Illustration** — embedded chart showing the concept in action.
3. **Analogy** — a common-life parallel to make the mechanism intuitive.
4. **Numeric example** — concrete numbers showing the concept in operation.
5. **Code** — runnable Python that implements the concept (linked + inline excerpt).
6. **Relationships** — links to related concepts within the chapter, beyond the chapter, and notes on when the concept works best vs. worst.

## Using this in Obsidian

1. Drop the `concepts/`, `images/`, and `codes/` folders into your Obsidian vault (or a chapter subfolder). They are siblings — keep that structure intact so the relative links resolve.
2. Open `00_Chapter14_Overview.md` first — it's the concept map.
3. The `[[wiki-link]]` syntax inside notes will resolve automatically once everything is in the vault.
4. Image embeds use `![[filename.png]]` — place `images/` alongside `concepts/`, or update Obsidian's attachment folder setting if you keep them elsewhere.
5. Code links use relative paths like `[[../codes/05_breakout.py]]` — they'll work as plain links inside Obsidian; for direct execution, open the file in your IDE.

## Running the code

All scripts are self-contained and depend only on `numpy` and `pandas`:

```bash
pip install numpy pandas matplotlib
cd codes/
python3 05_breakout.py
```

Each file uses a fixed random seed, so results are reproducible. The synthetic price series are deliberately small so the mechanism — not the backtest result — is the focus.

## Reading order suggestions

**For a one-pass overview** (≈ 30 min):
0 → 1 → 5 → 6 → 13

**For deep study** (≈ 2 hours):
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13

**By role:**
- **Builder track** (you'll implement a system): 5 → 6 → 7 → 11 → 13
- **Researcher track** (you'll backtest): 1 → 8 → 9 → 13 → then jump to Chapter 15
- **Skeptic track** (you want to know the failure modes): 12 → 7 → 11 → 13

## Cross-chapter map (selected)

| This chapter's concept | Connected chapter | Why |
|------|------|------|
| Pyramiding (10) | Ch. 8 | Chapter 8 explicitly notes pyramiding and midtrend entry are the same problem |
| Trade Exit (11) | Ch. 9 | Stop-loss vocabulary and stop placement principles |
| Countertrend (12) | Ch. 6 | Oscillators are the workhorse of countertrend systems |
| Filter (7) | Ch. 4 | Trading-range detection is the canonical filter input |
| Diversification (13) | Ch. 16 | Planned trading approach builds on these portfolio principles |
| All trend systems (1–9) | Ch. 15 | Every parameter introduced here becomes a test variable |
