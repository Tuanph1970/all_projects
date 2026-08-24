# Publishing the Mercai backend on `api.mercai.tuan1970.com`

Puts the mercai API behind Cloudflare via a tunnel, replacing the retired
`112.213.91.103` address. Nothing here is applied automatically — every step
below is one you run.

| | |
|---|---|
| Public hostname | `https://api.mercai.tuan1970.com` |
| Local origin | `http://localhost:8002` (`mercai_traefik`, published `8002:80`) |
| Tunnel | **new**, named `mercai` — *not* the existing `homelab` |
| Config template | `back_end/cloudflared/config.yml` |

---

## 0. Read this first — the TLS caveat

Cloudflare's free Universal SSL certificate covers `tuan1970.com` and
`*.tuan1970.com`, and **`*` matches one label only**. `api.mercai.tuan1970.com`
is two labels deep, so it is *not* covered. Until that is resolved the mobile
app will fail TLS validation against this hostname.

Three ways out, cheapest first:

1. **Use a single-level hostname instead** — `mercai-api.tuan1970.com`. Free,
   works immediately. Change one line in `front_end/src/constants/config.js`
   and the `hostname:` in the tunnel config.
2. **Advanced Certificate Manager** — ~$10/month on the zone, covers deeper
   subdomains.
3. **Cloudflare for SaaS / custom origin cert** — more setup than this is worth.

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
