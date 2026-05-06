"""
Concept 9 — Schwager's Corollary: "Bad simulations drive out good"
------------------------------------------------------------------
Realistic simulations look modest. Fantasy backtests look amazing.
In a marketplace where buyers compare numbers, the unrealistic ones
win attention — so honest sellers either lose business or start
inflating their numbers too.

This script just shows how absurd compounded fantasy returns become
once you do the math.

Run: python concept_09_schwagers_corollary.py
"""

def compound(initial, annual_pct, years):
    return initial * (1 + annual_pct / 100) ** years


initial = 100_000
years = 13

print(f"Starting capital : ${initial:,}")
print(f"Years            : {years}")
print()
print(f"{'Claimed annual return':<25} {'Implied final value':>25}")
print("-" * 52)

for r in [12, 25, 50, 100, 200, 400, 600]:
    final = compound(initial, r, years)
    label = "(realistic)" if r <= 25 else "(fantasy)"
    print(f"{r:>3}% {label:<20} ${final:>24,.0f}")

print()
print("$100k -> $1B in 13 years at 100% / yr.  Anyone advertising this")
print("is selling something other than honest backtests.")
print()
print("Lesson: refuse to compare 'simulated results' on advertised")
print("numbers alone. Demand the methodology.")
