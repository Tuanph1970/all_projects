#!/usr/bin/env bash
# Install one target's dependencies and run its unit tests — the single
# definition CI runs (.github/workflows/stockpredict-ci.yml at the repo root)
# and that can be run locally in a clean python:3.11 container to reproduce it.
#
# Usage (from stock_microservices/):
#   scripts/ci-unit-tests.sh <service-name>     e.g. stock-data-service
#   scripts/ci-unit-tests.sh <shared-lib-dir>   stock-common | chart-decomp-lib | event-reaction-lib
#
# Unit tests only: anything marked integration / e2e / performance needs live
# infrastructure (MySQL, RabbitMQ, Neo4j, the running stack) and is deselected,
# as is `slow` — research-grade validation runs (e.g. the VMD-HAR walk-forward
# guard), the same tier scripts/quick-test.sh skips.
set -euo pipefail

target="${1:?usage: ci-unit-tests.sh <service-name|shared-lib-dir>}"
cd "$(dirname "$0")/.."

pip_install() { python -m pip install --quiet --disable-pip-version-check "$@"; }

pip_install pytest pytest-asyncio pytest-timeout httpx aiosqlite

case "$target" in
  stock-common|chart-decomp-lib|event-reaction-lib)
    [ "$target" = event-reaction-lib ] && pip_install -e ./chart-decomp-lib
    # Two chart-decomp-lib tests reach into the service's API layer
    # (test_multiscale_service.py, test_report_fpr_column.py).
    [ "$target" = chart-decomp-lib ] && pip_install -r services/chart-decomp-service/requirements.txt
    pip_install -e "./$target"
    cd "$target"
    exec python -m pytest tests -q -m "not slow"
    ;;
esac

svc="services/$target"
[ -d "$svc" ] || { echo "unknown target: $target" >&2; exit 2; }

# Per-service install quirks, mirroring each service's Dockerfile.
case "$target" in
  prediction-service)
    # CPU wheel first, or requirements.txt pulls the multi-GB CUDA build.
    pip_install --index-url https://download.pytorch.org/whl/cpu torch
    pip_install -r "$svc/requirements.txt"
    ;;
  stock-data-service)
    # vnstock is no longer on PyPI; it installs only from the vendored wheels (#96).
    pip_install --find-links=vendor/wheels -r "$svc/requirements.txt"
    ;;
  chart-decomp-service)
    pip_install -r "$svc/requirements.txt" -e ./chart-decomp-lib
    ;;
  event-reaction-service)
    pip_install -r "$svc/requirements.txt" -e ./chart-decomp-lib -e ./event-reaction-lib
    ;;
  *)
    pip_install -r "$svc/requirements.txt"
    ;;
esac
pip_install -e ./stock-common

if [ -z "$(find "$svc/tests" -name 'test_*.py' -print -quit 2>/dev/null)" ]; then
  echo "::notice::no unit tests in $svc"
  exit 0
fi

# Run from stock_microservices/ so the shared pytest.ini applies; the
# service directory goes on the path so `import app` resolves to it.
export PYTHONPATH="$svc"
exec python -m pytest "$svc/tests" -q -m "not integration and not e2e and not performance and not slow"
