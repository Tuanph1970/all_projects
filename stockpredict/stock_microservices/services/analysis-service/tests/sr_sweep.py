"""EM-2 / W1 — `FR-EM-S10`: sweep every threshold, with its evidence.

Test-support, not a test module.

`CLAUDE.md` and `FR-EM-S10` both say the same thing: E&M's figures are
1940s–60s NYSE rules, so every number in EM-2 is a **default pending a
sweep**, never a trusted constant. This module is that sweep, and it is also
the one remaining thing that could overturn `S7`'s verdict — if a threshold
was badly chosen, EM-2 is understated across the board.

The trap this module exists to avoid
------------------------------------
The plan names it twice, because this workstream has paid for it twice
(EM-1 `S2`'s `confirm_rvol`, Backlog `#78`'s `MAX_PATTERN_AGE_BARS`):

    A parameter read as a DEFAULT ARGUMENT is bound at function-definition
    time. Patching the module constant afterwards does nothing, the sweep
    comes back perfectly flat, and a flat sweep reads as "this parameter does
    not matter" when it actually means "the harness never varied it".

In `sr_volume` the situation is worse than uniform — it is **mixed**:

* ``MAX_CONGESTION_BARS`` is read inside `congestion_span`'s body, so
  patching the module attribute **does** work;
* every other threshold is a default argument on a function that
  `_find_sr_levels` calls **without** passing it, so patching the module
  attribute is a **no-op**.

A naive module-constant sweep would therefore show one parameter appearing to
respond and the rest perfectly flat, which is the most misleading possible
output. `override()` below rebinds the *functions* in the namespace
`_find_sr_levels` actually calls, and `tests/test_sr_sweep_mechanism.py`
asserts every knob genuinely moves the result before any number here is
believed.

`MAX_CONGESTION_BARS` turned out to be a third case, found by that guard: it
is body-read *and* structurally inert, because `S4` calls the primitives once
per touch so no real span ever approaches it. It is listed in
`INERT_FOR_HS1` with its reason rather than swept to a flat row.

Trap (b), also from the plan: an improvement in a total that comes from
*doing less* is not an improvement (EM-9's net P&L rose 37% on 35% fewer
trades). Hit rate is a rate, so it is not directly vulnerable — but a setting
that collapses the sample can raise it by accident, so every row reports its
resolved count and `flag_small_sample` marks the ones to distrust.
"""
from __future__ import annotations

import contextlib
import functools
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import app.services.analysis_service as asvc
import app.services.sr_volume as srv

from tests.sr_hitrate_harness import run_study

#: The sweep runs at a reduced step so a grid finishes in minutes rather than
#: hours. 32 symbols is kept — `S4` established that 12 is too few for
#: comparisons — and every setting sees the identical sample, so the
#: *relative* readings are sound. The winning configuration is re-confirmed at
#: step 5 before anything is concluded.
SWEEP_SYMBOLS = 32
SWEEP_STEP = 10

#: Below this many resolved approaches a row is not trusted (trap b).
MIN_RESOLVED = 2_000

ARMS_OF_INTEREST = (
    "touch_count", "touch_count_matched",
    "em2_volume", "em2_role", "em2_adjusted", "random_null",
)


# ---------------------------------------------------------------------------
# The override machinery
# ---------------------------------------------------------------------------

#: Which function keyword each threshold actually reaches, in the namespace
#: `_find_sr_levels` calls. `None` means the constant is read in a function
#: body and is patched directly instead.
_KEYWORD_TARGETS: Dict[str, List[tuple]] = {
    "DEFAULT_BASELINE_WINDOW": [("aggregate_level_volume", "baseline_window")],
    "DEFAULT_NEIGHBOURHOOD": [
        ("aggregate_level_volume", "window"),
        ("level_price_cog", "window"),
    ],
    "BREAK_ATR_MULTIPLE": [
        ("detect_breaks", "atr_multiple"),
        ("detect_attacks", "atr_multiple"),
    ],
    "ATTACK_PROXIMITY_ATR": [("detect_attacks", "proximity_atr")],
    "AGE_HALFLIFE_BARS": [
        ("adjusted_level_strength", "halflife"),
        ("age_decay", "halflife"),
    ],
    "AGE_DECAY_FLOOR": [
        ("adjusted_level_strength", "floor"),
        ("age_decay", "floor"),
    ],
    "DISTANCE_AWAY_PCT": [("adjusted_level_strength", "distance_pct")],
    "DISTANCE_SUPPRESSION": [("adjusted_level_strength", "suppression")],
    # Body-read: patched as a module attribute on sr_volume.
    "MAX_CONGESTION_BARS": [],
}

#: Constants that `analysis_service` itself reads in a body, so they must be
#: patched in *that* module too.
_ALSO_PATCH_IN_SERVICE = {"DISTANCE_AWAY_PCT"}


@contextlib.contextmanager
def override(**params: Any) -> Iterator[None]:
    """Apply threshold overrides so `_find_sr_levels` actually sees them.

    Rebinds the functions in `analysis_service`'s namespace with the keyword
    pre-applied, and patches module attributes for the body-read constants.
    Everything is restored on exit.
    """
    saved_funcs: List[tuple] = []
    saved_attrs: List[tuple] = []

    try:
        for name, value in params.items():
            if name not in _KEYWORD_TARGETS:
                raise KeyError(f"unknown sweep parameter {name!r}")

            for func_name, keyword in _KEYWORD_TARGETS[name]:
                current: Callable = getattr(asvc, func_name)
                saved_funcs.append((func_name, current))
                setattr(asvc, func_name, functools.partial(current, **{keyword: value}))

            # Always patch the module constant too. It is a no-op for the
            # default-argument cases, which is exactly the trap — but it is
            # what makes the body-read ones work, and it keeps anything that
            # reads the constant for reporting consistent with the run.
            if hasattr(srv, name):
                saved_attrs.append((srv, name, getattr(srv, name)))
                setattr(srv, name, value)
            if name in _ALSO_PATCH_IN_SERVICE and hasattr(asvc, name):
                saved_attrs.append((asvc, name, getattr(asvc, name)))
                setattr(asvc, name, value)
        yield
    finally:
        for module, name, value in reversed(saved_attrs):
            setattr(module, name, value)
        for func_name, value in reversed(saved_funcs):
            setattr(asvc, func_name, value)


# ---------------------------------------------------------------------------
# Grids
# ---------------------------------------------------------------------------

#: Thresholds that cannot move `H-S1` by construction, with the reason. They
#: are excluded from the grid rather than swept to a flat row, because a flat
#: row is this module's signal for "the override failed" and overloading it
#: with "the parameter is inert" would make both unreadable.
INERT_FOR_HS1: Dict[str, str] = {
    "MAX_CONGESTION_BARS": (
        "A misuse guard, not a tuning knob. `S1` added it so a CLUSTER-WIDE "
        "call fails loudly, and `S4` complies by calling the primitives once "
        "per touch — so every real span is at most DEFAULT_NEIGHBOURHOOD+1 "
        "bars (4 at the default) and no grid setting from 15 upwards ever "
        "bites. Verified still functional: a 41-bar span with MAX=15 is "
        "refused. It becomes live only if DEFAULT_NEIGHBOURHOOD is pushed "
        "past about half of it, which no setting in this sweep does."
    ),
    "ATTACK_PROXIMITY_ATR": (
        "Nothing consumes `attacks`. `S6` measured E&M's third-attack rule, "
        "found the third attack penetrates 42.3% of the time against a "
        "predicted >50%, and the pre-registered consequence was that the "
        "weighting does not ship. So this threshold moves the reported "
        "`attacks` field and can move nothing else. That is a finding, not an "
        "omission."
    ),
}

GRIDS: Dict[str, List[Any]] = {
    # Congestion shape.
    "DEFAULT_NEIGHBOURHOOD": [1, 3, 5, 10],
    "DEFAULT_BASELINE_WINDOW": [50, 100, 200],
    # Penetration. E&M's own filter was 3% of price; this is the ATR form.
    "BREAK_ATR_MULTIPLE": [0.25, 0.5, 1.0, 2.0],
    # Age decay. E&M speak in years; a 250-bar window spans about one.
    "AGE_HALFLIFE_BARS": [40, 120, 250],
    "AGE_DECAY_FLOOR": [0.1, 0.4, 0.8],
    # Distance away. E&M's figure is 10%.
    "DISTANCE_AWAY_PCT": [5.0, 10.0, 20.0],
    "DISTANCE_SUPPRESSION": [0.2, 0.5, 0.9],
}


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def _row(report) -> Dict[str, Any]:
    arms = report.as_dict()["arms"]
    out: Dict[str, Any] = {}
    for arm in ARMS_OF_INTEREST:
        a = arms.get(arm)
        if not a:
            continue
        out[arm] = {
            "rate": a["hit_rate"],
            "resolved": a["hits"] + a["misses"],
        }
    return out


def z_vs(row: Dict[str, Any], a: str, b: str) -> Optional[float]:
    """Two-proportion z between two arms of one row."""
    if a not in row or b not in row:
        return None
    p1, n1 = row[a]["rate"], row[a]["resolved"]
    p2, n2 = row[b]["rate"], row[b]["resolved"]
    if not (p1 and p2 and n1 and n2):
        return None
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return (p1 - p2) / se if se else None


def flag_small_sample(row: Dict[str, Any]) -> List[str]:
    """Trap (b): a setting that collapses the sample can raise a rate by
    accident. Name the arms whose sample is too thin to read."""
    return [
        arm for arm, v in row.items()
        if v["resolved"] < MIN_RESOLVED
    ]


def sweep(
    parameters: Optional[List[str]] = None,
    symbols: int = SWEEP_SYMBOLS,
    step: int = SWEEP_STEP,
    out_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """One-at-a-time sweep. Returns ``{parameter: {setting: row}}``."""
    names = parameters or list(GRIDS)
    results: Dict[str, Any] = {
        "_config": {"symbols": symbols, "step": step, "min_resolved": MIN_RESOLVED},
        "parameters": {},
    }

    for name in names:
        results["parameters"][name] = {}
        for setting in GRIDS[name]:
            with override(**{name: setting}):
                report = run_study(max_symbols=symbols, step=step)
            row = _row(report)
            row["_flags"] = flag_small_sample(row)
            results["parameters"][name][str(setting)] = row
            best = row.get("em2_adjusted", {}).get("rate")
            print(f"  {name}={setting!r:>8}  em2_adjusted={best}  "
                  f"touch_count={row.get('touch_count', {}).get('rate')}",
                  flush=True)
            if out_path:
                out_path.write_text(json.dumps(results, indent=2, sort_keys=True))
        print(f"{name}: done", flush=True)

    return results


#: Which arm each parameter can actually move. Checking flatness against the
#: wrong arm manufactures a false alarm: `BREAK_ATR_MULTIPLE` feeds breaks,
#: so it moves `em2_role` and leaves `em2_adjusted` identical — which is
#: correct behaviour, not a failed override. Found while reading the first
#: partial results, and worth stating because "flat" is this module's bug
#: signal and a false one would discredit the real ones.
ARM_OF_EFFECT: Dict[str, str] = {
    "DEFAULT_NEIGHBOURHOOD": "em2_volume",
    "DEFAULT_BASELINE_WINDOW": "em2_volume",
    "BREAK_ATR_MULTIPLE": "em2_role",
    "AGE_HALFLIFE_BARS": "em2_adjusted",
    "AGE_DECAY_FLOOR": "em2_adjusted",
    "DISTANCE_AWAY_PCT": "em2_adjusted",
    "DISTANCE_SUPPRESSION": "em2_adjusted",
}


def is_flat(param_rows: Dict[str, Any], arm: str = "em2_adjusted") -> bool:
    """The harness-smell detector.

    A parameter whose every setting returns an identical rate **on the arm it
    feeds** was almost certainly never applied. That is a bug report, not a
    finding. Pass the arm from `ARM_OF_EFFECT`: checking the wrong one reports
    a false alarm.
    """
    rates = {
        row.get(arm, {}).get("rate")
        for key, row in param_rows.items()
        if not key.startswith("_")
    }
    return len(rates) <= 1


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/em2_sweep.json")
    names = sys.argv[2:] or None
    print(f"EM-2 W1 sweep -> {target}  ({SWEEP_SYMBOLS} symbols, step {SWEEP_STEP})",
          flush=True)
    data = sweep(parameters=names, out_path=target)

    print("\nflatness check (a flat parameter means the override failed):")
    for name, rows in data["parameters"].items():
        arm = ARM_OF_EFFECT.get(name, "em2_adjusted")
        verdict = "FLAT - SUSPECT" if is_flat(rows, arm) else "varies"
        print(f"  {name:<26} on {arm:<14} {verdict}")
