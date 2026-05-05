# Chapter 8 — Midtrend Entry and Pyramiding

Study notes derived from Schwager, *Getting Started in Technical Analysis*, Chapter 8.

## Folder layout

```
Chapter_08_Midtrend_Entry_Pyramiding/
├── obsidian/         ← drop into your Obsidian vault as-is
│   ├── Chapter_08_Index.md
│   ├── Midtrend_Entry.md
│   ├── Percent_Retracement.md
│   ├── Reversal_of_Minor_Reaction.md
│   ├── Continuation_Pattern_Breakout.md
│   ├── Reaction_to_Long_Term_MA.md
│   └── Pyramiding.md
├── images/           ← referenced by the .md files via ![[…]] syntax
│   └── 0[1–6]_*.png
└── code/             ← runnable Python implementation of each concept
    ├── 01_midtrend_entry.py        (engine / orchestrator)
    ├── 02_percent_retracement.py
    ├── 03_reversal_minor_reaction.py
    ├── 04_continuation_breakout.py
    ├── 05_long_term_ma_reaction.py
    └── 06_pyramiding.py            (with three risk guards)
```

## Using in Obsidian

1. Copy the `obsidian/` folder contents into a `Schwager/Ch08/` folder inside your vault.
2. Copy `images/` into the same folder (or your vault's attachments folder).
3. Start at `Chapter_08_Index.md` — it links to everything else.

## Running the code

Each `.py` file is self-contained and runnable:

```bash
pip install numpy pandas
python3 code/02_percent_retracement.py
```

Each one creates synthetic price data, applies the strategy, prints the
entries it would have generated, and asserts a basic invariant.

## Concept dependencies

```
Midtrend_Entry  ─┬─► Percent_Retracement
                 ├─► Reversal_of_Minor_Reaction
                 ├─► Continuation_Pattern_Breakout
                 └─► Reaction_to_Long_Term_MA
                            │
                            ▼
                       Pyramiding   (re-uses any of the four as triggers
                                     + 3 risk-control rules)
```
