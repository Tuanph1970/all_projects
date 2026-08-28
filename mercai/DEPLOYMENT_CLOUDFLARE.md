# Publishing the Mercai backend on `mercai-api.tuan1970.com`

**✅ LIVE since 2026-08-28.** Kept as a runbook for rebuilding it elsewhere.

| | |
|---|---|
| Public hostname | `https://mercai-api.tuan1970.com` |
| Local origin | `http://localhost:8002` (`mercai_traefik`, published `8002:80`) |
| Tunnel | `mercai`, id `2dbc8dbc-7484-49f9-8111-26c8ac76b64b` |
| Config | `back_end/cloudflared/config.yml` (filled in, not a template any more) |

---

## 0. The TLS caveat — resolved by flattening the hostname

Cloudflare's free Universal SSL covers `tuan1970.com` and `*.tuan1970.com`, and
**`*` matches one label only**. `api.mercai.tuan1970.com` is two labels deep and
would *not* have been covered, so the app would have failed TLS on every
request.

**Decision 2026-08-28: use `mercai-api.tuan1970.com`.** One label, free, works
today. Verified: the served certificate is `CN=tuan1970.com` from Google Trust
Services and `curl` reports `SSL certificate verify ok`.

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
cloudflared tunnel route dns mercai api.mercai.tuan1970.com
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
# Health through the tunnel — expect JSON, not a Cloudflare error page
curl -s https://api.mercai.tuan1970.com/api/v1/ai/health | python3 -m json.tool

# Auth route reachable — expect 401 (no token), which proves routing works
curl -s -o /dev/null -w '%{http_code}\n' https://api.mercai.tuan1970.com/api/v1/auth/me

# Uploaded images resolve on the same hostname
curl -s -o /dev/null -w '%{http_code}\n' https://api.mercai.tuan1970.com/static/uploads/
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

## Verified 2026-08-28

Run from this machine over public HTTPS, after `cloudflared tunnel run mercai`:

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

### Still to do

The tunnel is running in the foreground under the current shell. For it to
survive a logout or reboot it needs a systemd unit — remember `--origincert`,
or move `cert.pem` and the credentials JSON into `/etc/cloudflared/`.
