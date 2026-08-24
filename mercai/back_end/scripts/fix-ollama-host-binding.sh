#!/bin/bash
# ============================================================================
# Make the host's Ollama reachable from the ai-service container.
# ============================================================================
# Ollama defaults to binding 127.0.0.1:11434, which containers cannot reach:
# ai-service talks to http://host.docker.internal:11434 (the docker bridge
# gateway). Without this, /api/v1/ai/health reports "ollama": "unreachable"
# and every AI feature stays hidden in the client.
#
# HOW THE BINDING IS SET DEPENDS ON HOW OLLAMA WAS INSTALLED:
#
#   snap    -- configured through snapctl, NOT the environment. The snap's
#              launcher does `OLLAMA_HOST=$(snapctl get host)` on line 4 and
#              exports that, so a systemd Environment= drop-in is overwritten
#              before ollama ever starts. `snap set` is the only thing that
#              works. (An earlier version of this script used a drop-in and
#              silently did nothing.)
#   native  -- reads OLLAMA_HOST from the environment, so a systemd drop-in
#              on ollama.service is correct.
#
# Run with: sudo ./scripts/fix-ollama-host-binding.sh
# ============================================================================
set -euo pipefail

BIND="${OLLAMA_BIND:-0.0.0.0:11434}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Must run as root: sudo $0" >&2
    exit 1
fi

if snap list ollama >/dev/null 2>&1; then
    INSTALL=snap
elif systemctl list-unit-files ollama.service >/dev/null 2>&1; then
    INSTALL=native
else
    echo "No ollama snap and no ollama.service found. Nothing to configure." >&2
    exit 1
fi
echo "==> Detected a $INSTALL install"

if [ "$INSTALL" = snap ]; then
    # Remove the drop-in the earlier version of this script installed. It never
    # had any effect, and leaving it in place implies a binding that is not real.
    STALE=/etc/systemd/system/snap.ollama.listener.service.d/override.conf
    if [ -f "$STALE" ] && grep -q OLLAMA_HOST "$STALE"; then
        echo "==> Removing the ineffective systemd drop-in from the previous attempt"
        rm -f "$STALE"
        rmdir --ignore-fail-on-non-empty "$(dirname "$STALE")"
        systemctl daemon-reload
    fi

    echo "==> snap set ollama host=$BIND"
    snap set ollama host="$BIND"
    snap restart ollama.listener
else
    DROPIN_DIR=/etc/systemd/system/ollama.service.d
    echo "==> Installing systemd drop-in with OLLAMA_HOST=$BIND"
    mkdir -p "$DROPIN_DIR"
    printf '[Service]\nEnvironment=OLLAMA_HOST=%s\n' "$BIND" > "$DROPIN_DIR/override.conf"
    systemctl daemon-reload
    systemctl restart ollama.service
fi

# A duplicate /usr/local/bin/ollama unit cannot start when the snap owns the
# port and had been restart-looping tens of thousands of times.
if [ "$INSTALL" = snap ] && systemctl list-unit-files ollama.service >/dev/null 2>&1; then
    echo "==> Disabling the duplicate ollama.service restart loop"
    systemctl disable --now ollama.service || true
fi

echo "==> Waiting for Ollama to come back up"
for _ in $(seq 1 30); do
    curl -sf -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 1
done

echo "==> Listening sockets (want 0.0.0.0, not 127.0.0.1):"
ss -tlnp | grep 11434 || echo "    (nothing on 11434 -- check: journalctl -u snap.ollama.listener -n 40)"

echo "==> Reachability from a container:"
docker run --rm --add-host=host.docker.internal:host-gateway curlimages/curl:latest \
    -s -m 5 -o /dev/null -w "    host.docker.internal:11434 -> HTTP %{http_code}\n" \
    http://host.docker.internal:11434/api/tags || true

echo
echo "Expect HTTP 200 and a 0.0.0.0 bind. Anything else means it did not take."
echo "If ufw is active, restrict the port to Docker only:"
echo "    sudo ufw allow from 172.16.0.0/12 to any port 11434 proto tcp"
echo "    sudo ufw deny 11434"
