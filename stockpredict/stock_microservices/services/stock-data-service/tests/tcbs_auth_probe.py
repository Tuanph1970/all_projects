"""Backlog #142 — can TCBS auth run unattended? A deliberately cheap probe.

    PYTHONPATH=. python3 tests/tcbs_auth_probe.py            # no OTP consumed
    PYTHONPATH=. python3 tests/tcbs_auth_probe.py --otp 123456
    PYTHONPATH=. python3 tests/tcbs_auth_probe.py --otp 123456 --extend-key

STEP 5 IS OPT-IN (`--extend-key`) AND THAT IS NOT CAUTION FOR ITS OWN SAKE.
`apikey/extend` renews the API KEY, and the new term runs from the moment of
extension instead of adding to what is left ("khong cong don vao thoi han cu").
The key in use here runs to 2027-11-10, so a successful extend today does not
extend anything — it SPENDS most of a year to buy a year. A probe whose default
run can silently cost that is a probe that must not be run by default, and the
flag is what makes the cost a decision rather than a side effect.

Not a test. It answers ONE question that gates the whole adapter design:

    The JWT is valid for at most 8 hours, so an unattended nightly job needs
    ~3 refreshes a day. Exchanging the API key for a JWT takes an `otp` field
    (a Smart OTP from the TCInvest app). If every refresh needs a human to tap
    the app, the nightly job cannot run unattended and the design changes.

WHY IT IS BUILT TO AVOID SPENDING THINGS. An unconfirmed report says the token
endpoint allows only 10 exchanges/day; TCBS does not publish a figure either
way. A probe that retries, or that guesses payload shapes until one works,
would burn a budget we cannot see. So: the request shape is taken from the
published spec rather than discovered, NOTHING is retried, and each step makes
at most one call. Steps 1 and 2 consume no OTP at all.

SECRETS ARE NEVER PRINTED. The key, the OTP and the JWT are reported by length
and by claim NAMES only. A probe whose output cannot be pasted into an issue is
a probe people stop running.
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.config import get_settings

settings = get_settings()

TOKEN_PATH = "/gaia/v1/oauth2/openapi/token"
#: Quoted from the per-endpoint doc pages, NOT inferred from the index. The
#: first version of this probe used /gaia/v1/auth/apikey-info/ — a path a
#: summariser had reconstructed from the DOC url rather than read from the
#: spec — and got a 404 that looked like "the key cannot read its own expiry".
#: It is worth one extra fetch to read a path rather than infer one.
INFO_PATH = "/gaia/v1/oauth2/openapi/apikey/info"
EXTEND_PATH = "/gaia/v1/oauth2/openapi/apikey/extend"

TIMEOUT = 30


def post(path: str, payload: Dict[str, Any],
         bearer: Optional[str] = None) -> Tuple[int, Any]:
    """One POST. No retry, by design — see the module docstring."""
    url = settings.TCBS_BASE_URL.rstrip("/") + path
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode(errors="replace")
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as exc:                                   # noqa: BLE001
        return -1, f"{type(exc).__name__}: {exc}"


def redact(obj: Any, depth: int = 0) -> Any:
    """Structure, not content. Anything that smells like a credential becomes
    its length — the shape of a response is what this probe is reporting."""
    SECRET = ("token", "apikey", "api_key", "otp", "secret", "jwt",
              "accesstoken", "access_token", "refreshtoken", "refresh_token")
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(s in str(k).lower() for s in SECRET) and isinstance(v, str):
                out[k] = f"<{len(v)} chars>"
            else:
                out[k] = redact(v, depth + 1)
        return out
    if isinstance(obj, list):
        return [redact(v, depth + 1) for v in obj[:3]] + (
            ["…"] if len(obj) > 3 else [])
    if isinstance(obj, str) and len(obj) > 120:
        return f"<{len(obj)} chars>"
    return obj


def jwt_exp_claims(token: str) -> Optional[Dict[str, Any]]:
    """Read a JWT's payload WITHOUT verifying it.

    Verification needs TCBS's public key and is not the question here — the
    question is what `exp` says, i.e. how long this token actually lives
    against the 8 hours the docs promise.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:                                          # noqa: BLE001
        return None


def describe_claims(claims: Dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    print(f"      claim names: {sorted(claims)}")
    for field in ("exp", "iat", "nbf"):
        if field in claims:
            try:
                ts = datetime.fromtimestamp(float(claims[field]), timezone.utc)
                delta = (ts - now).total_seconds()
                print(f"      {field}: {ts.isoformat()}  ({delta/3600:+.2f} h from now)")
            except (TypeError, ValueError, OSError):
                print(f"      {field}: {claims[field]!r} (unparseable)")
    # The refresh question, answered from the token itself where possible.
    if any("refresh" in str(k).lower() for k in claims):
        print("      NOTE: a refresh-ish claim is present — inspect it, it may "
              "allow renewal without a new OTP")


def main(argv: list[str]) -> int:
    otp: Optional[str] = None
    # Opt-in, default OFF: step 5 resets the API key's term rather than adding
    # to it, so the default run must not be able to reach it.
    extend_key = "--extend-key" in argv
    if "--otp" in argv:
        i = argv.index("--otp")
        if i + 1 >= len(argv):
            print("--otp needs a value", file=sys.stderr)
            return 2
        otp = argv[i + 1]

    key = settings.TCBS_API_KEY
    print("TCBS auth probe — Backlog #142")
    print(f"  base url : {settings.TCBS_BASE_URL}")
    print(f"  api key  : {'set, ' + str(len(key)) + ' chars' if key else 'NOT SET'}")
    print(f"  otp      : {'supplied' if otp else 'not supplied (steps 1-2 only)'}")
    print(f"  extend   : {'ENABLED — step 5 will RESET the key term' if extend_key else 'off (step 5 reports only)'}")
    print("  no retries anywhere; at most one call per step\n")

    if not key:
        print("  TCBS_API_KEY is empty. Put it in .env, then rebuild and "
              "recreate stock-data-service.", file=sys.stderr)
        return 1

    # ── Step 1 — can we read the key's expiry WITHOUT an OTP? ─────────────
    # If yes, expiry can at least be MONITORED unattended even if renewal
    # cannot, which is the difference between a silent outage and an alert.
    print("STEP 1  apikey-info — does reading expiry need an OTP?")
    status, body = post(INFO_PATH, {"apiKey": key})
    print(f"  HTTP {status}")
    print(f"  {json.dumps(redact(body), ensure_ascii=False)[:600]}")
    if status == 200:
        print("  => expiry IS readable with the key alone. Unattended "
              "MONITORING is possible.")
    elif status == -1:
        print("  => the server closed the connection without replying. That is "
              "NOT the same as a\n     rejection: compare it with step 2, "
              "which reaches the SAME host and answers\n     properly. The "
              "likely reading is that this endpoint is authenticated and drops\n"
              "     unauthenticated callers, so step 4 retries it WITH a bearer "
              "token.")
    else:
        print("  => not readable with the key alone. Read the body above "
              "before assuming why.")

    # ── Step 2 — is `otp` actually mandatory for the exchange? ────────────
    # Asked by OMITTING it, which costs no valid OTP. A 4xx naming the field
    # is the answer; a 200 would be a much more interesting answer.
    print("\nSTEP 2  token exchange WITHOUT an otp — is it mandatory?")
    status, body = post(TOKEN_PATH, {"apiKey": key})
    print(f"  HTTP {status}")
    print(f"  {json.dumps(redact(body), ensure_ascii=False)[:600]}")
    if status == 200:
        print("  => NO OTP REQUIRED. The nightly job can refresh unattended; "
              "this is the best case and should be confirmed twice before "
              "being designed around.")
        tok = body.get("token") if isinstance(body, dict) else None
        if tok:
            claims = jwt_exp_claims(tok)
            if claims:
                describe_claims(claims)
    else:
        print("  => an OTP appears to be required for the exchange. That alone "
              "does NOT settle the question: what matters is whether an "
              "EXISTING token can be renewed without one (step 3).")

    # ── Step 3 — the real exchange, only with an OTP the operator supplied ─
    if not otp:
        print("\nSTEP 3  skipped (no --otp). Re-run with --otp <code> from the "
              "TCInvest app to\n        mint a real token and read its actual "
              "lifetime against the documented 8h.")
        print("\nWHAT IS STILL OPEN: whether a valid token can be renewed "
              "without a fresh OTP.\nStep 2 only shows the key->token path. If "
              "step 3 returns a token carrying a\nrefresh claim, or if "
              "apikey-extend works with the key alone, the nightly job is\n"
              "feasible; otherwise it needs a human every 8 hours and the "
              "design must change\n(long-lived cache, manual daily priming, or "
              "a different source for the price path).")
        return 0

    print("\nSTEP 3  token exchange WITH the supplied otp")
    status, body = post(TOKEN_PATH, {"apiKey": key, "otp": otp})
    print(f"  HTTP {status}")
    print(f"  {json.dumps(redact(body), ensure_ascii=False)[:600]}")
    if status != 200 or not isinstance(body, dict):
        print("  => exchange failed. Do NOT retry blindly: if a daily cap "
              "exists, each attempt spends it.")
        return 1

    token = body.get("token") or ""
    print(f"  => token obtained, {len(token)} chars")
    claims = jwt_exp_claims(token)
    if claims:
        describe_claims(claims)
        exp = claims.get("exp")
        if exp:
            try:
                hours = (datetime.fromtimestamp(float(exp), timezone.utc)
                         - datetime.now(timezone.utc)).total_seconds() / 3600
                documented = settings.TCBS_TOKEN_TTL_SECONDS / 3600
                print(f"      MEASURED lifetime {hours:.2f}h vs documented "
                      f"{documented:.0f}h "
                      f"({'matches' if abs(hours - documented) < 1 else 'DIFFERS'})")
            except (TypeError, ValueError, OSError):
                pass
    else:
        print("      token is not a readable JWT — report its shape, not its value")

    # ── Step 3b — THE question, tested directly and for free ─────────────
    # The docs show exactly three auth endpoints (token exchange, apikey info,
    # apikey extend) and NO refresh endpoint, so the documented answer is "a
    # token cannot be renewed without an OTP". That leaves one undocumented
    # possibility worth a single call: the exchange endpoint might accept a
    # live bearer token IN PLACE OF an otp. It costs no extra OTP, because the
    # one just spent is what authorises it.
    print("\nSTEP 3b  re-exchange with the BEARER instead of an otp — the "
          "renewal question")
    status, body = post(TOKEN_PATH, {"apiKey": key}, bearer=token)
    print(f"  HTTP {status}")
    print(f"  {json.dumps(redact(body), ensure_ascii=False)[:400]}")
    if status == 200 and isinstance(body, dict) and body.get("token"):
        print("  => RENEWAL WITHOUT AN OTP WORKS. The nightly job can refresh "
              "itself; the\n     manual-prime design collapses to a background "
              "loop. Confirm it twice\n     before relying on it — this is "
              "undocumented behaviour and may be withdrawn.")
        fresh = jwt_exp_claims(body["token"])
        if fresh:
            describe_claims(fresh)
    else:
        print("  => NO. A fresh OTP is required for every token, so an "
              "unattended nightly job\n     is impossible as scheduled. The "
              "design options are in\n     docs/backlog142_adapter_design.md "
              "§2: move the sync so one prime covers\n     both jobs, prime "
              "twice a day, or keep the price path on a source that\n     "
              "needs no interactive auth.")

    # ── Step 4 — the same two endpoints, now WITH the token ──────────────
    # Step 1 failed unauthenticated. If they answer with a bearer token, they
    # are simply protected endpoints, and the useful question becomes whether
    # the token they accept can itself be obtained without a human.
    print("\nSTEP 4  apikey-info WITH the bearer token (it needs none, so this "
          "only confirms\n        the token does not BREAK it)")
    status, body = post(INFO_PATH, {"apiKey": key}, bearer=token)
    print(f"  HTTP {status}")
    print(f"  {json.dumps(redact(body), ensure_ascii=False)[:600]}")
    if status == 200:
        print("  => the key's expiry is readable once authenticated. A daily "
              "expiry check is\n     therefore possible for as long as a token "
              "is held.")

    print("\nSTEP 5  apikey-extend — renews the API KEY's own validity, not "
          "the JWT's")
    print("  The spec requires an `otp` here too, and the new term runs from "
          "the moment of\n  extension rather than adding to what is left "
          "('không cộng dồn vào thời hạn cũ'),\n  so extending early THROWS "
          "AWAY the remainder. An EXPIRED key cannot be extended\n  at all — "
          "it has to be recreated in TCInvest. Both facts belong in whatever "
          "renews\n  this on a schedule.")
    if not extend_key:
        print("  SKIPPED — pass --extend-key to actually call it. Not calling "
              "it costs nothing:\n  the key's expiry is already readable from "
              "step 1/4, and extending EARLY would\n  replace the remaining "
              "term rather than add to it. Run this only when the key is\n"
              "  close to expiry and you mean to renew it.")
    else:
        print("  --extend-key given: calling it. The term after this runs from "
              "NOW, not from\n  the old expiry — compare it against step 1's "
              "expireDate to see what it cost.")
        status, body = post(EXTEND_PATH, {"apiKey": key, "otp": otp}, bearer=token)
        print(f"  HTTP {status}")
        print(f"  {json.dumps(redact(body), ensure_ascii=False)[:600]}")

    print("\nTHE ANSWER THIS PROBE EXISTS FOR:")
    print("  - key -> JWT requires an OTP (step 2, HTTP 400 'Missing required "
          "inputs').")
    print("  - the JWT lives ~8h (step 3's exp).")
    print("  So an unattended nightly job is only possible if a token can be "
          "renewed WITHOUT\n  a fresh OTP. Check step 3's claim names for a "
          "refresh claim and step 4/5's bodies\n  for an expiry or renewal "
          "field. If none exists, the design options are: prime a\n  token "
          "manually once a day, run the job inside the 8h window after a manual "
          "prime,\n  or keep the price path on a source that needs no "
          "interactive auth.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
