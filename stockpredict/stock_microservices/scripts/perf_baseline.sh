#!/usr/bin/env bash
#
# Capture a quick p50/p95/p99 baseline against a running gateway.
#
# Usage:
#   ./scripts/perf_baseline.sh                   # default: localhost:8004
#   GATEWAY=http://staging:8004 ./scripts/perf_baseline.sh
#   ./scripts/perf_baseline.sh --requests 500    # heavier sweep
#
# Phase 3.5 target: p99 < 300ms for cached-response endpoints.
# Output: a markdown table row per endpoint, suitable for pasting into
# ROADMAP.xlsx → Sessions Log "What I learned / decided".
#
# Tools: prefers `hey` if installed (https://github.com/rakyll/hey); falls
# back to a small Python loop with httpx if not. No-op if neither is available.

set -euo pipefail

GATEWAY="${GATEWAY:-http://localhost:8004}"
REQUESTS=200
CONCURRENCY=10

while [[ $# -gt 0 ]]; do
    case "$1" in
        --requests) REQUESTS="$2"; shift 2 ;;
        --concurrency) CONCURRENCY="$2"; shift 2 ;;
        --gateway) GATEWAY="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,15p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown arg: $1" >&2
            exit 2
            ;;
    esac
done

# Endpoints chosen to be safe to hammer: unauthenticated, cached, idempotent,
# and confirmed to return 2xx through the Traefik gateway (no 307/401/404).
ENDPOINTS=(
    "stock-list|/stock_helper/api/v2/companies?limit=20"
    "indices|/stock_helper/api/v2/market/indices"
    "journal-info|/stock_helper/api/v2/journal/info"
)

echo "Gateway:      $GATEWAY"
echo "Requests:     $REQUESTS  (concurrency $CONCURRENCY)"
echo

if command -v hey >/dev/null 2>&1; then
    runner="hey"
elif command -v python3 >/dev/null 2>&1; then
    runner="python"
else
    echo "Neither 'hey' nor 'python3' is available; install one to run the baseline." >&2
    exit 3
fi

echo "| Endpoint | p50 (ms) | p95 (ms) | p99 (ms) | rps | failures |"
echo "|----------|----------|----------|----------|-----|----------|"

for entry in "${ENDPOINTS[@]}"; do
    label="${entry%%|*}"
    path="${entry##*|}"
    url="${GATEWAY}${path}"

    if [[ "$runner" == "hey" ]]; then
        # `hey` prints a "Latency distribution" block we parse out.
        out="$(hey -n "$REQUESTS" -c "$CONCURRENCY" -m GET "$url" 2>/dev/null || true)"
        p50_ms=$(echo "$out" | awk '/50% in/ {print $3*1000}' | head -1)
        p95_ms=$(echo "$out" | awk '/95% in/ {print $3*1000}' | head -1)
        p99_ms=$(echo "$out" | awk '/99% in/ {print $3*1000}' | head -1)
        rps=$(echo "$out" | awk '/Requests\/sec/ {print $2}' | head -1)
        failures=$(echo "$out" | awk '/Status code distribution/ {flag=1;next} flag && /\[/ {if($1!="[200]") s+=$2} END {print s+0}')
    else
        out="$(GATEWAY="$GATEWAY" REQUESTS="$REQUESTS" CONCURRENCY="$CONCURRENCY" \
            python3 - <<PY 2>/dev/null
import asyncio, os, statistics, time
import httpx
url = os.environ['GATEWAY'].rstrip('/') + "$path"
n = int(os.environ.get('REQUESTS', 200))
c = int(os.environ.get('CONCURRENCY', 10))

async def main():
    timings = []
    failures = 0
    sem = asyncio.Semaphore(c)
    async with httpx.AsyncClient(timeout=10.0) as client:
        async def one():
            nonlocal failures
            async with sem:
                t0 = time.perf_counter()
                try:
                    r = await client.get(url)
                    if r.status_code >= 400:
                        failures += 1
                except Exception:
                    failures += 1
                    return
                timings.append((time.perf_counter() - t0) * 1000.0)
        start = time.perf_counter()
        await asyncio.gather(*(one() for _ in range(n)))
        elapsed = time.perf_counter() - start
    if not timings:
        print('NA NA NA 0.0 %d' % failures); return
    timings.sort()
    def pct(p):
        idx = max(0, int(round(p / 100.0 * (len(timings)-1))))
        return timings[idx]
    print(f"{pct(50):.1f} {pct(95):.1f} {pct(99):.1f} {len(timings)/elapsed:.1f} {failures}")

asyncio.run(main())
PY
)"
        read -r p50_ms p95_ms p99_ms rps failures <<<"$out"
    fi

    printf "| %-12s | %-8s | %-8s | %-8s | %-3s | %-8s |\n" \
        "$label" "${p50_ms:-NA}" "${p95_ms:-NA}" "${p99_ms:-NA}" "${rps:-NA}" "${failures:-NA}"
done

echo
echo "Target (Phase 3.5): p99 < 300ms for cached endpoints."
