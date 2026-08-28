#!/usr/bin/env bash
# Install the `mercai` Cloudflare tunnel as a systemd service.
#
# Without this the tunnel runs in a foreground shell and dies at logout or
# reboot, which is a confusing outage: DNS still resolves, so the app gets a
# Cloudflare 1033 rather than a connection error.
#
# WHAT THIS TOUCHES, AND WHY IT IS SAFE
#   /etc/cloudflared/config.yml currently holds the OLD `homelab` config for
#   stock.tuan1970.com. That config names tunnel 0b83d79d-…, which no longer
#   exists on the Cloudflare account, and cloudflared.service is disabled —
#   so it is already inert. Stock now runs from a different machine. This
#   script backs it up before replacing it, rather than assuming.
#
#   The packaged unit at /etc/systemd/system/cloudflared.service already runs
#   `--config /etc/cloudflared/config.yml tunnel run` as root, so no new unit
#   is written. Only its config changes.
#
# Idempotent: safe to re-run.
#
#   sudo back_end/scripts/install-tunnel-service.sh

set -euo pipefail

TUNNEL_ID="2dbc8dbc-7484-49f9-8111-26c8ac76b64b"
TUNNEL_NAME="mercai"
HOSTNAME_FQDN="mercai-api.tuan1970.com"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_HOME="${SUDO_USER:+/home/$SUDO_USER}"
USER_HOME="${USER_HOME:-$HOME}"
CF_HOME="$USER_HOME/.cloudflared"

if [[ $EUID -ne 0 ]]; then
    echo "This needs root: sudo $0" >&2
    exit 1
fi

echo "==> Checking sources"
for f in "$CF_HOME/cert.pem" "$CF_HOME/$TUNNEL_ID.json"; do
    [[ -f "$f" ]] || { echo "    missing: $f" >&2; exit 1; }
    echo "    found $f"
done

echo "==> Backing up any existing config"
if [[ -f /etc/cloudflared/config.yml ]]; then
    if cmp -s /etc/cloudflared/config.yml "$SRC_DIR/cloudflared/config.yml"; then
        echo "    already installed and identical, nothing to back up"
    else
        BACKUP="/etc/cloudflared/config.yml.bak.$(date +%Y%m%d%H%M%S)"
        cp -a /etc/cloudflared/config.yml "$BACKUP"
        echo "    saved previous config to $BACKUP"
    fi
fi

echo "==> Installing credentials and config"
install -d -m 0755 /etc/cloudflared
install -m 0600 "$CF_HOME/$TUNNEL_ID.json" "/etc/cloudflared/$TUNNEL_ID.json"
install -m 0600 "$CF_HOME/cert.pem" /etc/cloudflared/cert.pem
install -m 0644 "$SRC_DIR/cloudflared/config.yml" /etc/cloudflared/config.yml
echo "    /etc/cloudflared/config.yml -> tunnel $TUNNEL_NAME ($TUNNEL_ID)"

echo "==> Stopping any foreground cloudflared for this tunnel"
# Only ours: killing every cloudflared would take down anything else the
# machine happens to be serving.
if pkill -f "tunnel run $TUNNEL_NAME" 2>/dev/null; then
    echo "    stopped a foreground instance"
    sleep 2
else
    echo "    none running"
fi

echo "==> Enabling the service"
systemctl daemon-reload
systemctl enable --now cloudflared
sleep 6
systemctl --no-pager --lines=0 status cloudflared | head -5 || true

echo
echo "==> Verifying over public HTTPS"
CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 \
        "https://$HOSTNAME_FQDN/api/v1/intel/health" || echo 000)"
if [[ "$CODE" == "200" ]]; then
    echo "    OK  https://$HOSTNAME_FQDN/api/v1/intel/health -> 200"
    echo
    echo "Done. The tunnel now survives logout and reboot."
    echo "Logs: journalctl -u cloudflared -f"
else
    echo "    FAILED: got HTTP $CODE" >&2
    echo "    journalctl -u cloudflared -n 40 --no-pager" >&2
    exit 1
fi
