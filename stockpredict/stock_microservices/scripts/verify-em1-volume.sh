#!/usr/bin/env bash
# EM-1 / F3 — deploy check for the volume-validation layer.
#
# Verifies against REAL market data the things no unit test can: that volume
# arrives non-NULL from stock-data-service, that the rules fire, and that the
# rebuilt frontend bundle actually carries the new strings.
#
# Usage:  ./scripts/verify-em1-volume.sh [SYMBOL ...]
#
# Note the local gateway is :18004, not 8004 — 8004 belongs to another stack on
# this machine. Override with GW=... if yours differs.
set -uo pipefail
GW="${GW:-http://localhost:18004}"
FE="${FE:-http://localhost:3004}"
PREFIX=/stock_helper/api/v2
SYMS=("${@:-VHM TCB POW STB VNM FPT HPG VCB}")
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok()  { echo "  PASS  $1"; pass=$((pass+1)); }
bad() { echo "  FAIL  $1"; fail=$((fail+1)); }

echo "=== 1. the EM-1 endpoint answers through the gateway ==="
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$GW$PREFIX/ai/insights/patterns/VHM?lookback_bars=60")
[ "$code" = "200" ] && ok "gateway -> ai-insights -> 200" || bad "gateway -> ai-insights -> $code"

echo "=== 2. the volume layer on real bars ==="
for S in ${SYMS[@]}; do
  curl -s --max-time 90 "$GW$PREFIX/ai/insights/patterns/$S?lookback_bars=250" -o "$TMP/$S.json" &
done
wait
python3 - "$TMP" <<'PY'
import json, sys, glob
from collections import Counter
tmp = sys.argv[1]
cards, comps = Counter(), Counter()
pats = moved = scored = climax = syms = 0
for f in sorted(glob.glob(f"{tmp}/*.json")):
    try: d = json.load(open(f))
    except Exception: continue
    syms += 1
    if d.get("volume_climax"): climax += 1
    for p in d.get("patterns", []):
        pats += 1
        ev = p.get("volume_evidence") or {}
        cards[ev.get("verdict")] += 1
        if p.get("volume_score") is not None: scored += 1
        if p.get("geometric_confidence") != p.get("confidence"): moved += 1
        for det in (ev.get("components") or {}).values():
            comps[det.get("verdict")] += 1
print(f"  symbols={syms}  patterns={pats}  scored={scored}  confidence_moved={moved}")
print(f"  card verdicts:      {dict(cards)}")
print(f"  component verdicts: {dict(comps)}")
print(f"  volume climax:      {climax}/{syms} symbols")
# The checks that matter. A screen full of neutral verdicts means missing
# volume data upstream, not a broken rule — EC-V1 degrades to neutral on NULL.
if pats == 0:            print("  FAIL  no patterns detected at all")
elif scored == 0:        print("  FAIL  nothing scored — volume is NULL upstream, or the layer is not deployed")
elif moved == 0:         print("  FAIL  no confidence moved — check volume data before suspecting the rules")
else:                    print("  PASS  volume is read and is moving confidence on real data")
if not comps.get("suspect"):
    print("  WARN  FR-EM-V4 'suspect' never fired in this sample (rare, but worth a wider sweep)")
PY

echo "=== 3. the rebuilt frontend bundle carries the new strings ==="
# This is the check that catches the classic mistake on this setup: a host
# `npm run build` does NOT update the running screen — the Docker image must
# be rebuilt. If these fail, the image is stale.
JS=$(curl -s --max-time 15 "$FE/stock-app/" | grep -oE '/stock-app/static/js/main\.[a-z0-9]+\.js' | head -1)
if [ -z "$JS" ]; then
  bad "could not locate main.js at $FE/stock-app/"
else
  curl -s --max-time 45 "$FE$JS" -o "$TMP/main.js"
  # Checked in Python, not grep: the minifier escapes non-ASCII string
  # literals, so the Vietnamese copy is present as \xNN sequences and a
  # literal grep for it reports a false MISSING. Both forms are accepted.
  python3 - "$TMP/main.js" <<'PY2'
import sys
raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
needles = [
    ("en", "Volume confirms"), ("en", "Volume suspect"),
    ("en", "volume_climax"), ("en", "chart_patterns_title"),
    ("vi", "Khối lượng xác nhận"), ("vi", "Khối lượng đáng ngờ"),
]
missing = []
for lang, s in needles:
    if s in raw or s.encode("unicode_escape").decode("ascii") in raw:
        print(f"  PASS  bundle has [{lang}] '{s}'")
    else:
        print(f"  FAIL  bundle MISSING [{lang}] '{s}' (stale image?)")
        missing.append(s)
sys.exit(1 if missing else 0)
PY2
  if [ $? -eq 0 ]; then pass=$((pass+6)); else fail=$((fail+1)); fi
fi

echo ""; echo "=== $pass passed, $fail failed ==="
[ "$fail" -eq 0 ]
