#!/usr/bin/env bash
# Hand the `mercai` Cloudflare tunnel over to another machine.
#
# THE ONE RULE: never run this tunnel on two machines at once. Cloudflare
# load-balances across every connected instance of a tunnel ID, so while both
# are up roughly half of all requests land on whichever machine is not serving
# the stack — an intermittent, geographically-random failure that looks like
# nothing and is miserable to diagnose. Stop it HERE before starting it THERE.
#
# Keeping the same tunnel id means DNS needs no change at all: the CNAME for
# mercai-api.tuan1970.com already points at <tunnel-id>.cfargotunnel.com, and
# that target is unchanged by which machine answers for it.
#
#   ./scripts/migrate-tunnel.sh plan          show what to copy and where
#   sudo ./scripts/migrate-tunnel.sh stop     stop + disable here (takes the API offline)
#
# `plan` needs no root and changes nothing.

set -euo pipefail

TUNNEL_ID="2dbc8dbc-7484-49f9-8111-26c8ac76b64b"
TUNNEL_NAME="mercai"
HOSTNAME_FQDN="mercai-api.tuan1970.com"
ACTION="${1:-plan}"

case "$ACTION" in
plan)
    cat <<EOF

Moving tunnel '$TUNNEL_NAME' ($TUNNEL_ID)
Serving https://$HOSTNAME_FQDN  ->  http://localhost:8002

BEFORE YOU START — the tunnel only forwards to localhost:8002, so the NEW
machine must be running the mercai stack. A tunnel without a backend behind it
answers 502, not 404, and looks like the app is broken rather than moved.

On the NEW machine
------------------
 1. Bring up the backend first, and prove it locally:
        git clone <repo> && cd mercai/back_end
        cp .env.example .env        # then set DB_PASSWORD, SECRET_KEY,
                                    # INTEL_PRICE_ENABLED
        docker compose -p mercai up -d --build
        curl -s localhost:8002/api/v1/intel/health     # must return healthy

 2. Bring the data across, or the catalogue is empty:
        # on THIS machine
        docker exec mercai_mysql mysqldump -umercai_user -p'<pw>' mercai > mercai.sql
        # on the NEW machine
        docker exec -i mercai_mysql mysql -umercai_user -p'<pw>' mercai < mercai.sql
    (or just run scripts/seed_catalogue.py there for test data)

 3. Install cloudflared, then copy these two files from this machine.
    They are SECRETS — use scp, never chat or email:

        sudo install -d -m 0755 /etc/cloudflared
        scp $USER@$(hostname -I 2>/dev/null | awk '{print $1}'):/tmp/${TUNNEL_ID}.json /tmp/
        # (run the 'stop' step here first — it stages the files readably)

 4. Put them in place and install the config from the repo:
        sudo install -m 0600 /tmp/${TUNNEL_ID}.json /etc/cloudflared/
        sudo install -m 0600 /tmp/cert.pem          /etc/cloudflared/
        sudo install -m 0644 back_end/cloudflared/config.yml /etc/cloudflared/config.yml
        shred -u /tmp/${TUNNEL_ID}.json /tmp/cert.pem

 5. Start it and verify from OUTSIDE that network:
        sudo systemctl enable --now cloudflared
        curl -s https://$HOSTNAME_FQDN/api/v1/intel/health

On THIS machine, once the new one is proven
-------------------------------------------
        sudo ./scripts/migrate-tunnel.sh stop

Only cert.pem is optional: 'tunnel run' needs the credentials JSON, while
cert.pem is what lets you manage tunnels (create/route/delete) from the new
machine. Copy it unless you want management to stay here.

Nothing changes in DNS. Do not create a second tunnel — that would need a CNAME
change and buys nothing.

EOF
    ;;

stop)
    if [[ $EUID -ne 0 ]]; then
        echo "This needs root: sudo $0 stop" >&2
        exit 1
    fi
    echo "==> Stopping and disabling cloudflared here"
    systemctl disable --now cloudflared || true
    systemctl is-active cloudflared >/dev/null 2>&1 \
        && { echo "    still active — check 'journalctl -u cloudflared'" >&2; exit 1; } \
        || echo "    stopped and disabled"

    echo "==> Staging the credentials for copying"
    # /etc/cloudflared is root-only, which is right, but it also means scp as a
    # normal user cannot read it. Stage a readable copy, and say plainly that
    # it must be destroyed afterwards.
    OWNER="${SUDO_USER:-root}"
    for f in "$TUNNEL_ID.json" cert.pem; do
        install -m 0600 -o "$OWNER" "/etc/cloudflared/$f" "/tmp/$f"
        echo "    /tmp/$f  (chmod 600, owned by $OWNER)"
    done

    cat <<EOF

    Copy them to the new machine, then DESTROY the staged copies:

        scp /tmp/$TUNNEL_ID.json /tmp/cert.pem <user>@<new-host>:/tmp/
        shred -u /tmp/$TUNNEL_ID.json /tmp/cert.pem

    https://$HOSTNAME_FQDN is now DOWN until the new machine starts the tunnel.
    Cloudflare will answer 1033 (tunnel not found) — DNS still resolves, so the
    app will look broken rather than absent. Keep the gap short.

EOF
    ;;

*)
    echo "usage: $0 [plan|stop]" >&2
    exit 1
    ;;
esac
