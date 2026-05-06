# Concept 9 — Schwager's Corollary: "Bad Simulations Drive Out Good"

**Tags:** #ch15 #market-dynamics #pitfall

## Definition

Schwager's tongue-in-cheek riff on Gresham's Law (which says "bad money drives out good" — overvalued currency stays in circulation while undervalued currency gets hoarded).

His corollary: in the marketplace of trading systems, **unrealistic ("bad") simulations drive realistic ("good") simulations out of view**. Honest backtests show modest numbers and lose buyer attention to flashy fictional ones. The seller who refuses to inflate gets out-marketed by the seller who does.

The seven primary distortion methods Schwager names:

1. **The Well-Chosen Example** — see [[01_Well_Chosen_Example]].
2. **Kitchen Sink Approach** — keep adding rules in hindsight to plaster over past losses.
3. **Ignoring Risk** — quote returns as % of margin or some unrealistically thin capital base.
4. **Overlooking Losing Trades** — show the chart points where the rules worked, hide the points where the same rules failed.
5. **Optimize, Optimize, Optimize** — search a huge parameter grid, report only the best result.
6. **Unrealistic Transaction Costs** — see [[04_Slippage_and_Realistic_Assumptions]].
7. **Fabrication** — outright making numbers up. (Yes, this happens. Schwager's "$299 man.")

## Illustration

![[09_schwagers_corollary.png]]

What different annual return claims compound to over 3 years (log scale). 18%/yr looks puny next to 100%, which looks puny next to 400%. Honest sellers can't compete on numbers without lying.

## Analogy

Three coffee shops on the same block. Café A puts a sign in the window: "Customers report a moderate boost in alertness." Café B's sign reads: "Doubles your productivity!" Café C: "Cured my insomnia, my back pain, and my mortgage." Café A is the only one telling the truth, and gets the least foot traffic. After a year, A either lies too or closes.

## Numeric example

From `code/concept_09_schwagers_corollary.py`, $100,000 starting capital, 13 years:

```
Claimed annual return       Implied final value
 12% (realistic)             $          436,344
 25% (realistic)             $        1,907,348
 50% (fantasy)               $       21,898,830
100% (fantasy)               $    1,073,741,824
200% (fantasy)               $   25,400,000,000+
400% (fantasy)               $   stops fitting in dollars
```

100% per year for 13 years turns $100k into **>$1 billion**. The math alone proves the claim is impossible — but it gets repeated in advertising every year.

## Source code

[[code/concept_09_schwagers_corollary.py]]

## Relationships

### Within the chapter
- The natural conclusion after Schwager has dismantled [[06_Testing_vs_Fitting]] — once you see how easy distortion is, the corollary explains why it's *commercially rewarded*.
- Each distortion method maps back to a specific safeguard:
  - Method 1 → [[07_Blind_Simulation]] / [[08_Average_Parameter_Set_Performance]]
  - Method 5 → [[05_Optimization]] (parameter stability)
  - Method 6 → [[04_Slippage_and_Realistic_Assumptions]]
  - Methods 2, 3, 4, 7 → demand methodology, not numbers

### When does this matter most?
Whenever you're evaluating a system you didn't build. Schwager's rule of thumb: weight on advertised "simulated results" should equal "the amount of money invested in the system: zero." Treat brochure numbers as marketing, not data.

### Outside the chapter
- [[Chapter_18_Market_Wizardom]] — successful traders consistently emphasize protection from fraudsters as part of the discipline.
- Behavioral economics — this is a textbook **adverse-selection** mechanism, parallel to Akerlof's "market for lemons."
