#!/bin/bash
# ============================================================================
# Make the host's Ollama reachable from the ai-service container.
# ============================================================================
# Ollama defaults to binding 127.0.0.1:11434, which containers cannot reach:
# ai-service talks to http://host.docker.internal:11434 (the docker bridge
# gateway, 172.17.0.1). Without this, /api/v1/ai/health reports
# "ollama": "unreachable" and every AI feature stays hidden in the client.
#
# This installs a systemd drop-in so the snap-packaged Ollama binds 0.0.0.0,
# and stops the broken /usr/local/bin/ollama unit that is in a restart loop.
#
# Run with: sudo ./scripts/fix-ollama-host-binding.sh
# ============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Must run as root: sudo $0" >&2
    exit 1
fi

UNIT=snap.ollama.listener.service
DROPIN_DIR="/etc/systemd/system/${UNIT}.d"

echo "==> Binding Ollama to 0.0.0.0:11434"
mkdir -p "$DROPIN_DIR"
cat > "$DROPIN_DIR/override.conf" <<'CONF'
[Service]
# Bind all interfaces so Docker containers can reach Ollama over the bridge
# gateway (host.docker.internal). Pair this with a firewall rule if the host
# is on an untrusted network -- Ollama has no authentication of its own.
Environment=OLLAMA_HOST=0.0.0.0:11434
CONF

# The duplicate /usr/local/bin/ollama unit cannot start (it has no write access
# to /usr/share/ollama) and has been restart-looping tens of thousands of times.
if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
    echo "==> Disabling the broken ollama.service restart loop"
    systemctl disable --now ollama.service || true
fi

systemctl daemon-reload
systemctl restart "$UNIT"

echo "==> Waiting for Ollama to come back up"
for _ in $(seq 1 30); do
    if curl -sf -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "==> Listening sockets:"
ss -tlnp | grep 11434 || echo "    (nothing on 11434 -- check: journalctl -u $UNIT -n 40)"

echo "==> Reachability from a container:"
docker run --rm --add-host=host.docker.internal:host-gateway curlimages/curl:latest \
    -s -m 5 -o /dev/null -w "    host.docker.internal:11434 -> HTTP %{http_code}\n" \
    http://host.docker.internal:11434/api/tags || true

echo
echo "Expect HTTP 200. If ufw is active, restrict the port to Docker only:"
echo "    sudo ufw allow from 172.16.0.0/12 to any port 11434 proto tcp"
echo "    sudo ufw deny 11434"
