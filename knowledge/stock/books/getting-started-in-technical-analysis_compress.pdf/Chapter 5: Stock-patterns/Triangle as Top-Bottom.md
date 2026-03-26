---
tags: [technical-analysis, schwager, top-bottom-formation, triangle-reversal]
source: "Schwager Ch.5 pp.104-105"
related: ["[[Top and Bottom Formations MOC]]", "[[Triangles]]"]
---

# Triangle as Top/Bottom Formation

## The Dual Identity
The same triangle structure that acts as a continuation pattern mid-trend becomes a potential reversal pattern after an extended move.

> Triangles, which are among the most common continuation patterns, can be top and bottom formations as well. — Schwager

## Key Consideration
The breakout direction still determines interpretation. After a long advance, a triangle that breaks **downward** = top formation. After a long decline, a triangle that breaks **upward** = bottom formation.

## No Separate Detection Needed
The `detect_triangles` function from [[Triangles]] handles both contexts. The interpretation depends on the preceding trend context, not the triangle's geometry.

## How to Distinguish Continuation from Reversal
Add a `preceding_trend_duration` field. If the triangle forms after 50+ bars of sustained trend, weight the possibility of reversal higher. If it forms mid-trend after a short impulse, default to continuation.

## Connections
- [[Triangles]] — the base pattern (detection code lives there)
- Breakout direction > triangle type — Schwager's universal rule applies here too
