# Publishing the Mercai backend on `mercai.tuan1970.com`

**✅ LIVE on `https://mercai.tuan1970.com`.** Verified over public HTTPS
2026-09-03: register, login, `/auth/me`, refresh, products and the chat
WebSocket all pass.

> **⚠️ The deployment moved (2026-09-03).** The backend was reinstalled on a
> **different computer**, and the hostname changed with it:
> `mercai-api.tuan1970.com` → **`mercai.tuan1970.com`**. The old name is dead —
> it answers Cloudflare **1033**, which reads to a user as "the backend is
> broken" rather than "it moved". Everything below is written from the point of
> view of *whichever machine runs the stack*; this one no longer does.

| | |
|---|---|
| Public hostname | `https://mercai.tuan1970.com` |
| Origin | `http://localhost:8002` (`mercai_traefik`, published `8002:80`) **on the serving machine** |
| Runs on | Another computer, since 2026-09-03. This machine's `cloudflared` is `inactive` |
| Tunnel | `mercai`, id `2dbc8dbc-…` **as created here on 2026-08-28** — not confirmed to be the id in use on the new machine. Run `cloudflared tunnel list` there to check |
| Config | `back_end/cloudflared/config.yml` |
| Dead name | `mercai-api.tuan1970.com` — 1033, do not use |

### Known gap on the new machine

`intel-service` is **not deployed there**: `/api/v1/intel/health` returns 404
publicly while the same path answers 200 on a local stack. The price
intelligence routes are therefore unavailable in production until intel is
brought up on that machine. Auth, products, cart, users and chat are all fine.

The database there is also **fresh** — a newly registered user came back as
`id: 2` and `GET /api/v1/products/` returns `[]`. Either `mysqldump` the
catalogue across or run `back_end/scripts/seed_catalogue.py` on that machine.

---

## 0. The TLS caveat — resolved by flattening the hostname

Cloudflare's free Universal SSL covers `tuan1970.com` and `*.tuan1970.com`, and
**`*` matches one label only**. `api.mercai.tuan1970.com` is two labels deep and
would *not* have been covered, so the app would have failed TLS on every
request.

**Decision: keep the name one label deep.** That was `mercai-api.tuan1970.com`
on 2026-08-28 and is `mercai.tuan1970.com` since 2026-09-03 — the rename
changes nothing here, because both are single-label. Free, and works today.
Verified on the current host: the served certificate is `CN=tuan1970.com` from
Google Trust Services and `curl` reports `SSL certificate verify ok`.

The alternative was Advanced Certificate Manager at ~$10/month to keep the
deeper name. Not worth it for a naming preference.

---

## 0b. What the account actually looked like

Worth recording, because two things were not what the earlier notes assumed:

- `~/.cloudflared/0b83d79d-….json` is **stale** — that tunnel no longer exists
  on the account. It cannot be used and should not be referenced.
- The account had exactly one live tunnel, `homelab`
  (`90a553cf-…`), which serves `stock.tuan1970.com` from a different machine.
  **Never point a second machine at that ID:** Cloudflare load-balances across
  every connected instance of a tunnel ID, so half of stock's traffic would
  arrive here and 404. The same rule applies to `mercai` — to move it, either
  create a second tunnel and re-point DNS, or copy the credentials and stop it
  here first.
- `cloudflared` looks for `/etc/cloudflared/cert.pem` by default and this
  machine's lives in `~/.cloudflared/`, which fails with *"cannot read … to
  load origin certificate"*. The config sets `origincert` explicitly; a systemd
  unit needs the same.

Everything else below is unaffected by which hostname you pick.

---

## 1. Do not reuse the `homelab` tunnel

`homelab` (`0b83d79d-287c-4e02-9cac-15b5f129f7da`) serves
`stock.tuan1970.com` and now runs on the other PC. Cloudflare load-balances
across every connected instance of a tunnel ID, so pointing a second machine at
`homelab` would send roughly half of the stock app's traffic to a box whose
ingress rules do not mention it, and it would 404.

A tunnel reaches its own machine's `localhost`. The mercai stack runs here, so
mercai needs a tunnel that runs here too.

---

## 2. Create the tunnel

```bash
# Authenticates in a browser and drops cert.pem in ~/.cloudflared
cloudflared tunnel login

# Creates the tunnel; prints the ID and writes <ID>.json
cloudflared tunnel create mercai
```

## 3. Install the config

```bash
TUNNEL_ID=<the id printed above>

sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/"$TUNNEL_ID".json /etc/cloudflared/
sudo cp ~/.cloudflared/cert.pem          /etc/cloudflared/
sudo chmod 600 /etc/cloudflared/"$TUNNEL_ID".json /etc/cloudflared/cert.pem

# Fill the placeholder in the template as it is copied into place
sudo sed "s/TUNNEL_ID/$TUNNEL_ID/g" \
  ~/TuanPH/all_projects/mercai/back_end/cloudflared/config.yml \
  | sudo tee /etc/cloudflared/config.yml >/dev/null

cloudflared tunnel ingress validate
```

`ingress validate` reads `/etc/cloudflared/config.yml` and fails loudly on a
malformed rule — do not skip it.

## 4. Route DNS

```bash
cloudflared tunnel route dns mercai mercai.tuan1970.com
```

This creates a proxied CNAME pointing at the tunnel *ID*, not at a machine. If
you later move mercai to another box, move the credentials file — the DNS record
does not change.

## 5. Run it

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
systemctl status cloudflared --no-pager
```

## 6. Verify

```bash
B=https://mercai.tuan1970.com

# Auth route reachable — expect 401 (no token), which proves routing works.
# A JSON 401 is the pass; an HTML Cloudflare error page is not.
curl -s -w '\n%{http_code}\n' $B/api/v1/auth/me

# Public read path — expect 200
curl -s -o /dev/null -w '%{http_code}\n' $B/api/v1/products/

# Full auth round trip — expect 200 and a token
curl -s -X POST $B/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"<user>","password":"<pass>"}'

# Chat WebSocket — expect "101 Switching Protocols". Needs --http1.1:
# over HTTP/2 curl cannot send an Upgrade header and you get a misleading 404.
curl -s -i --http1.1 -N \
  -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  "$B/api/v1/chat/ws/<user_id>?token=<access_token>" | head -3
```

A `530`/`1033` means the tunnel is not connected. A TLS error means section 0.

---

## Limits worth knowing

- **Upload size.** Cloudflare's free plan caps a request body at **100 MB**.
  The video upload feature (`VIDEO_UPLOAD_FEATURE_PLAN.md`) has to stay under
  that, or move to direct-to-storage uploads that bypass the tunnel.
- **Response time.** The edge gives up at **100 seconds** (error 524). AI
  generation worst case is ~50s with `OLLAMA_TIMEOUT_SECONDS=25` and the one
  retry in `ollama_client.generate_json`. Raising that setting past ~45 puts
  you at risk of 524s.
- **The tunnel does not authenticate.** Everything Traefik routes becomes
  publicly reachable on this hostname. The Traefik dashboard is on `:8080`,
  a separate published port with no ingress rule, so it stays private — keep
  it that way.
- **Ollama.** Must be bound to `0.0.0.0:11434` for the containers to reach it
  (see `back_end/scripts/fix-ollama-host-binding.sh`). On the snap install this
  is `snap set ollama host=...`, **not** a systemd `Environment=` drop-in — the
  snap's launcher overwrites `OLLAMA_HOST` from `snapctl get host` before
  starting, so a drop-in silently does nothing. Ollama has no authentication of
  its own. It has no ingress rule so the tunnel never exposes it, but do
  firewall the port if this host sits on an untrusted network.

---

## Verified 2026-09-03 — on `mercai.tuan1970.com`, after the move

Run over public HTTPS against the new machine:

| Check | Result |
|---|---|
| `POST /api/v1/auth/register` | `200`, user created |
| `POST /api/v1/auth/login` | `200`, access + refresh, `expires_in: 1800` |
| `GET /api/v1/auth/me` + bearer token | `200`, `last_login` updated |
| `POST /api/v1/auth/refresh` | `200`, new token pair |
| Login with wrong password | `401 Incorrect username or password` |
| Register duplicate email | `400 Email already registered` |
| Register weak password | `422` with field detail |
| `GET /api/v1/products/`, `/products/categories` | `200` (catalogue is **empty**) |
| `GET /api/v1/cart/`, `/users/me/profile` unauth | `401` — routes live |
| **WebSocket** `wss://…/api/v1/chat/ws/{id}?token=…` | **`101 Switching Protocols`** |
| TLS | `CN=tuan1970.com`, Google Trust Services, verify ok |
| Warm latency (login) | ~0.65s total, TLS 0.06s |
| `GET /api/v1/intel/health` | **`404` — intel-service not deployed there** |

A third gotcha, met while verifying the WebSocket: `curl` negotiates **HTTP/2**
against Cloudflare, and cannot send an `Upgrade` header over it — the handshake
comes back **404** and looks exactly like a missing route. Pass `--http1.1` and
the same request returns `101`.

---

## Verified 2026-08-28 (historical — the original machine)

Run from the original machine over public HTTPS, after
`cloudflared tunnel run mercai`, when the hostname was still
`mercai-api.tuan1970.com`:

| Check | Result |
|---|---|
| `GET /api/v1/intel/health` | `200`, `SSL certificate verify ok` |
| `GET /api/v1/products/` | `200` |
| `POST /api/v1/auth/login` | token returned for a seeded seller |
| `GET /api/v1/intel/products/{id}/price-position` | full payload incl. external comparable and Tiki benchmark |
| **WebSocket** `wss://…/api/v1/chat/ws/{user_id}?token=…` | **upgraded and stayed open** — the piece most likely to break through a tunnel |
| Traefik dashboard `/dashboard/`, `/api/rawdata` | **404 publicly**, `200` on `localhost:8080` — the tunnel exposes only `:8002` |
| Warm latency | ~0.11–0.12s |

Two gotchas met on the way, both worth remembering:

- The chat WebSocket path is `/api/v1/chat/ws/{user_id}`, not `/api/v1/chat/ws`.
  The bare path 404s, which looks like a tunnel failure and is not.
- `UID` is a **readonly bash variable**. `UID=$(mysql … )` silently leaves it as
  the shell's own uid (1000), and the WebSocket then 403s on a user mismatch.
  Use any other name.

### Running as a service — done 2026-08-28 on the original machine

**This machine's `cloudflared` is now `inactive` and stays that way.** The notes
below describe installing the service on whichever machine serves the stack —
which since 2026-09-03 is the other computer, not this one.

    sudo back_end/scripts/install-tunnel-service.sh

The script takes `TUNNEL_ID`, `TUNNEL_NAME` and `HOSTNAME_FQDN` from the
environment now, so a machine with its own tunnel does not need the file edited:

    sudo TUNNEL_ID=<its-id> back_end/scripts/install-tunnel-service.sh

Idempotent. Installs the credentials and config into `/etc/cloudflared/`, stops
only the foreground instance of *this* tunnel, enables the packaged
`cloudflared.service`, and verifies public HTTPS before reporting success.

No new unit is written: the packaged one already runs
`--config /etc/cloudflared/config.yml tunnel run` as root, so only its config
changes. Because the files now live in `/etc/cloudflared/`, `origincert` is
where cloudflared looks by default and no flag is needed — but a CLI command
run from a user shell still needs `--origincert ~/.cloudflared/cert.pem`.

**It replaced stock's leftover config**, which was safe and was checked rather
than assumed: that file named tunnel `0b83d79d-…` (which no longer exists on
the account), `cloudflared.service` was disabled, and stock now runs from a
different machine. The previous file is kept at
`/etc/cloudflared/config.yml.bak.<timestamp>`. If this machine ever needs to
serve stock as well, add a second `ingress` rule to the one config rather than
swapping files — one tunnel can front many hostnames.

Verified after the switch: service `enabled` and `active`, exactly one
cloudflared process (systemd's), four edge connections, and login,
price-position, the chat WebSocket and the dashboard-404 check all still
passing over public HTTPS.

---

## Moving the tunnel to another machine

    back_end/scripts/migrate-tunnel.sh plan     # what to copy, in order
    sudo back_end/scripts/migrate-tunnel.sh stop

**Keep the same tunnel id where you can.** The CNAME for `mercai.tuan1970.com`
points at `<tunnel-id>.cfargotunnel.com`, and that target does not care which
machine answers. Moving the credentials therefore needs **no DNS change at
all**. Creating a second tunnel means re-pointing DNS and waiting on
propagation.

Note that the 2026-09-03 move did change the hostname, so DNS was touched
regardless. Whether that move reused tunnel `2dbc8dbc-…` or created a new one is
not recorded here — confirm with `cloudflared tunnel list` on the serving
machine before relying on the id in `cloudflared/config.yml`.

**Never run one tunnel id on two machines at once.** Cloudflare load-balances
across every connected instance, so while both are up roughly half of all
requests land on whichever machine is not serving the stack. The result is
intermittent and geographically random — the hardest shape of failure to
diagnose. Stop it here before starting it there.

### The dependency that is easy to miss

The tunnel forwards to `http://localhost:8002`, which is Traefik **on the same
machine**. Moving the tunnel alone does not move the backend: the new machine
must be running the mercai stack first, or the hostname answers 502. Bring the
stack up there and prove `curl localhost:8002/api/v1/intel/health` before
touching the tunnel.

The database moves separately too — a fresh stack has an empty catalogue, so
either `mysqldump` this one across or run `scripts/seed_catalogue.py` on the new
machine for test data.

### Which files are secret

| File | Needed to run? | Notes |
|---|---|---|
| `<tunnel-id>.json` | **yes** | The credential. Treat like a password |
| `cert.pem` | no | Account-level; only needed to *manage* tunnels (create/route/delete) from that machine |
| `config.yml` | yes | Not secret — it lives in `back_end/cloudflared/config.yml` |

`/etc/cloudflared` is root-only, so `migrate-tunnel.sh stop` stages readable
copies in `/tmp` for `scp`. **`shred -u` them afterwards** — the script says so,
because a tunnel credential left in `/tmp` is a live key to your origin.

### During the gap

DNS keeps resolving while no tunnel is connected, so Cloudflare answers **1033
(tunnel not found)** rather than a connection error. To anyone using the app
that reads as "the backend is broken", not "it is being moved". Keep the window
short, and prefer bringing the new machine fully up first so the switch is
seconds rather than minutes.
