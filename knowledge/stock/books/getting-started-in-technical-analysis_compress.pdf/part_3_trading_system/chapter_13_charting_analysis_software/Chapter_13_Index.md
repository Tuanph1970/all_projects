# Chapter 13 — Charting and Analysis Software
**Book:** Getting Started in Technical Analysis — Jack D. Schwager  
**Part:** Three — Trading Systems  
**Pages:** 221–225

---

## Chapter Overview
Chapter 13 bridges the gap between technical analysis *theory* and *practice* by explaining how traders acquire price data and choose the software tools to analyse it. Schwager argues that modern charting software has liberated traders from the laborious manual charting of the past — but choosing the wrong tool or data type is a costly mistake.

---

## Concepts in This Chapter

| # | Concept | File |
|---|---------|------|
| 1 | [[Historical Price Data]] | `concepts/historical_price_data.md` |
| 2 | [[End-of-Day Price Data]] | `concepts/end_of_day_data.md` |
| 3 | [[Real-Time (Tick) Price Data]] | `concepts/real_time_data.md` |
| 4 | [[Software Selection Framework]] | `concepts/software_selection.md` |
| 5 | [[Data Quality and Cleaning]] | `concepts/data_cleaning.md` |
| 6 | [[Continuous Futures Data]] | `concepts/continuous_futures.md` |

---

## Concept Relationship Map

```
Price Data Types
├── Historical Price Data  ←→  End-of-Day Price Data  ←→  Real-Time Data
│       ↑ cheaper / longer history        ↑ daily updates        ↑ expensive / intraday
│
└── Data Quality & Cleaning  (applies to ALL data types)
        ↓
Futures-Specific Data
└── Continuous Futures Data  (special case of Historical Data for futures)

Software Selection
├── feeds into → what DATA TYPE you need
└── governed by → Time Frame + Goals + Skills + Budget
```

---

## Cross-Chapter Links
- [[Chapter 2 - Types of Charts]] → bar charts, candlestick, P&F mentioned as outputs of software
- [[Chapter 6 - Oscillators]] → indicators applied within analysis software
- [[Chapter 14 - Technical Trading Systems]] → system testing is a software feature
- [[Chapter 15 - Testing and Optimizing Trading Systems]] → requires quality historical data

---

## Key Takeaway (Schwager's Advice)
> *"There is no point in paying for features you will not use."*  
> Match software to your actual time frame, analytical goal, and skill level. Start modest; upgrade later at a discount.

---

**Tags:** #technical-analysis #software #price-data #trading-tools #chapter13
