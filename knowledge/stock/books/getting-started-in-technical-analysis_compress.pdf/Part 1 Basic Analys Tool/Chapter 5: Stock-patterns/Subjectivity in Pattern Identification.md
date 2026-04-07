---
tags: [technical-analysis, schwager, meta-concept, subjectivity]
source: "Schwager Ch.1 pp.13-15; Ch.7 pp.123-125; Ch.8 p.132; Ch.12 pp.178-179; Ch.18 p.300"
related: ["[[Signal Frequency vs Reliability Trade-off]]", "[[Confirmation vs Anticipation]]", "[[Pattern Context]]", "[[Pattern Combinations]]"]
---

# Subjectivity in Pattern Identification

## Schwager's Position

Schwager is unusually candid — he doesn't pretend chart analysis is objective:

> Chart analysis is a very subjective endeavor. — Ch. 12

> Even technical analysts using the same patterns may interpret these patterns differently. One analyst's double top is another's trading range consolidation. — Ch. 12

> Since to some extent chart patterns are in the eye of the beholder, this approach will reflect a degree of subjectivity. — Ch. 8

## Why It's a Feature, Not a Bug

If patterns could be mechanized, everyone would trade them identically, and the edge would vanish (see reflexivity argument in [[Signal Frequency vs Reliability Trade-off]]). Subjectivity keeps chart analysis viable:

> The skill and subjectivity implied in this approach place chart analysis in the realm of an art that cannot be mimicked by merely following a set of textbook rules. This is a crucial point in understanding how the chartist approach can remain valid despite widespread publicity. — Ch. 7

## The Nine Ambiguities

In Ch. 1, Schwager lists nine objections to a simple trading-range/breakout definition — demonstrating that even the most basic pattern resists objective specification. Width, duration, outlier days, trend context, penetration threshold, number of closes, time lag — all are judgment calls.

## Analogy: Medical Diagnosis

Pattern identification is like reading an X-ray. The data is objective, but the interpretation requires training and experience. A radiologist with 20 years sees things a first-year resident misses. Chart analysis works the same way.

## Implication for Code

Create parameterized detectors that produce *candidates*. The parameters encode your interpretation — they're where subjectivity enters the system. Code demands precision; patterns resist it. The resolution: candidate screening + human (or heuristic) filtering.

## The Individualization Principle

> Each practitioner of chart analysis must choose an individual set of technical tools and define a personal analytical style. — Ch. 12

> The specific choice of confirmation conditions is one of the pivotal ways in which chart analysis is individualized. — Ch. 7

The method must match the personality (Ch. 18, Rule #3). Schwager resolved his own conflict by moving to mechanical systems — not because they're superior, but because they matched his puzzle-solving personality.
