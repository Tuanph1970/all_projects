#!/usr/bin/env python3
"""Backlog #142 — prime the TCBS OpenAPI token from a Smart OTP.

    ./stock_microservices/scripts/tcbs_prime.py            # prompt for the OTP
    ./stock_microservices/scripts/tcbs_prime.py --status    # look, spend nothing
    ./stock_microservices/scripts/tcbs_prime.py --force     # replace a live token

WHY A SCRIPT AND NOT A CURL LINE. The prime endpoint is admin-gated, so calling
it by hand means minting a JWT, finding the gateway port and shaping a JSON body
— three things to get wrong while a 30-second OTP ticks. Everything here that
can be checked without the OTP is checked BEFORE the prompt appears, so by the
time you are typing six digits the only thing left that can fail is the OTP
itself.

STDLIB ONLY, DELIBERATELY. No requests, no PyJWT, no dotenv. An ImportError
while you are holding a live OTP costs a code; the HS256 signing this needs is
twelve lines of `hmac`.

THE OTP IS SPENT PER TOKEN, NOT PER QUERY. One code mints one JWT that then
authorises every data call for its ~8-hour life, so this is about one tap per
token window — not one per request.

ONE ATTEMPT, NO RETRY, matching TcbsAuth.prime. An unconfirmed report puts the
token exchange at 10/day and TCBS publishes no figure, so nothing here loops: a
malformed code is rejected locally (free) and re-prompted, while a REJECTED
exchange stops and hands the decision back to you.

The OTP is never written to a file, a log or this script's output. It is echoed
as you type it, which is a deliberate trade: a six-digit single-use code that
expires in seconds is worth less than catching a typo before spending it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(REPO_ROOT, ".env")

DEFAULT_GATEWAY = os.environ.get("STOCK_GATEWAY_URL", "http://localhost:18004")
API_BASE = "/stock_helper/api/v2"
PRIME_PATH = f"{API_BASE}/stocks/tcbs/prime"
STATUS_PATH = f"{API_BASE}/stocks/tcbs/status"

#: The admin JWT exists for the length of one HTTP call. Short on purpose: it
#: is a credential minted outside auth-service, so it should not outlive its
#: errand.
ADMIN_JWT_TTL_SECONDS = 300

ICT = timezone(timedelta(hours=7))

#: From docs/backlog142_adapter_design.md §2 — the two jobs a token has to
#: cover, in UTC because the container runs UTC. They are 8h15m apart and the
#: token lives 8h, which is the finding that shaped the whole design; this
#: script reports which of them the token you just minted will actually reach.
SCHEDULED_JOBS = (
    ("daily company/price sync", 1, 0),
    ("momentum scanner (#133)", 9, 15),
)

TIMEOUT = 30


def read_env_file(path: str) -> Dict[str, str]:
    """Parse KEY=VALUE from .env without sourcing it.

    Not `source`d, and not passed through a shell: this file holds the JWT
    secret and the TCBS key, and nothing in it should ever be executed.
    """
    out: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return out


def mint_admin_jwt(secret: str, algorithm: str) -> str:
    """HS256 admin token for the two admin-gated TCBS endpoints.

    stock-data-service validates with the shared JWT_SECRET_KEY and, at
    ENVIRONMENT=production, requires role=admin (api/dependencies.py).
    """
    if algorithm.upper() != "HS256":
        raise SystemExit(f"JWT_ALGORITHM={algorithm} unsupported here; this "
                         "script signs HS256 only")
    now = int(time.time())

    def seg(obj: Dict[str, Any]) -> bytes:
        raw = json.dumps(obj, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    signing = seg({"alg": "HS256", "typ": "JWT"}) + b"." + seg({
        "sub": os.environ.get("TCBS_PRIME_USER_ID", "1"),
        "email": "ops@local",
        "role": "admin",
        "type": "access",
        "iat": now,
        "exp": now + ADMIN_JWT_TTL_SECONDS,
    })
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signing, hashlib.sha256).digest()).rstrip(b"=")
    return (signing + b"." + sig).decode()


def call(method: str, url: str, bearer: str,
         payload: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    """One HTTP call. Returns (status, body); never raises, never retries."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(body or "{}")
        except ValueError:
            return exc.code, {"detail": body[:300]}
    except Exception as exc:                                   # noqa: BLE001
        return -1, {"detail": f"{type(exc).__name__}: {exc}"}


def fmt_expiry(iso: Optional[str]) -> str:
    if not iso:
        return "unknown"
    try:
        exp = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    left = (exp - datetime.now(exp.tzinfo or timezone.utc)).total_seconds()
    return (f"{exp.astimezone(ICT):%Y-%m-%d %H:%M} ICT "
            f"({left / 3600:.2f} h from now)")


def report_coverage(token_expires: Optional[str], margin_seconds: int = 600) -> None:
    """Which scheduled job the new token still reaches.

    The point of printing this: one prime cannot cover both jobs as currently
    scheduled (they are 8h15m apart, the token lives 8h). Saying so at prime
    time is how that stops being a surprise at 09:15 UTC.
    """
    if not token_expires:
        return
    try:
        exp = datetime.fromisoformat(token_expires)
    except ValueError:
        return
    usable_until = exp - timedelta(seconds=margin_seconds)
    now = datetime.now(timezone.utc)
    print(f"\n  usable until {usable_until.astimezone(ICT):%H:%M} ICT "
          f"(10-min safety margin before {exp.astimezone(ICT):%H:%M})")
    for name, hh, mm in SCHEDULED_JOBS:
        nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        ok = nxt <= usable_until
        print(f"    {'COVERED    ' if ok else 'NOT COVERED'} {name:<26} "
              f"next run {nxt:%H:%M} UTC / {nxt.astimezone(ICT):%H:%M} ICT")


def prompt_otp() -> Optional[str]:
    """Six digits, then ENTER.

    Shape is validated HERE rather than by the vendor, because a typo that
    reaches TCBS may spend an exchange from a budget nobody can measure. Empty
    input aborts without spending anything.
    """
    while True:
        try:
            raw = input("  Smart OTP (6 digits), then ENTER: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  aborted — nothing spent.")
            return None
        otp = re.sub(r"[\s-]", "", raw)
        if not otp:
            print("  empty — aborted, nothing spent.")
            return None
        if re.fullmatch(r"\d{6}", otp):
            return otp
        print(f"  not six digits ({len(otp)} char(s)) — not sent. "
              "Re-read the code in TCInvest; a fresh one is free.")


def main(argv: list[str]) -> int:
    status_only = "--status" in argv
    force = "--force" in argv
    gateway = DEFAULT_GATEWAY.rstrip("/")
    if "--url" in argv:
        i = argv.index("--url")
        if i + 1 >= len(argv):
            print("--url needs a value, e.g. --url http://localhost:18004")
            return 2
        gateway = argv[i + 1].rstrip("/")

    env = read_env_file(ENV_FILE)
    secret = os.environ.get("JWT_SECRET_KEY") or env.get("JWT_SECRET_KEY", "")
    algorithm = os.environ.get("JWT_ALGORITHM") or env.get("JWT_ALGORITHM", "HS256")

    print("TCBS token prime — Backlog #142\n")
    print("Preflight — nothing below costs an OTP")
    print(f"  gateway    : {gateway}")
    if not secret:
        print(f"  JWT secret : MISSING. Expected JWT_SECRET_KEY in {ENV_FILE}")
        return 2
    print(f"  JWT secret : read from {os.path.relpath(ENV_FILE, REPO_ROOT)}, "
          f"{len(secret)} chars")
    bearer = mint_admin_jwt(secret, algorithm)
    print(f"  admin JWT  : minted {algorithm.upper()}, valid "
          f"{ADMIN_JWT_TTL_SECONDS // 60} min")

    code, body = call("GET", gateway + STATUS_PATH, bearer)
    if code != 200:
        print(f"  status     : HTTP {code} — "
              f"{json.dumps(body, ensure_ascii=False)[:300]}")
        print("\n  Not priming: the preflight failed, so a typed OTP would be "
              "spent on a call\n  that cannot succeed. Fix the above first — "
              "401 means the JWT secret does not\n  match the running service; "
              "-1 means the gateway is unreachable "
              "(./deploy.sh --status).")
        return 1

    present = body.get("token_present")
    print(f"  token now  : "
          f"{'present, expires ' + fmt_expiry(body.get('token_expires')) if present else 'none'}"
          f"{'' if present else ' — needs prime'}")
    key_exp = body.get("api_key_expires")
    if body.get("api_key_configured"):
        days = body.get("api_key_days_left")
        warn = " ** RENEW SOON **" if body.get("api_key_renew_soon") else ""
        print(f"  api key    : expires {key_exp}"
              f"{f', {days} days left' if days is not None else ''}{warn}")
    else:
        print("  api key    : NOT CONFIGURED in the service — set TCBS_API_KEY "
              "in .env and\n               recreate stock-data-service "
              "before priming")
        return 2

    if status_only:
        report_coverage(body.get("token_expires"))
        return 0

    if not body.get("needs_prime") and not force:
        print("\n  A usable token is already stored — not asking for an OTP. "
              "Pass --force to\n  replace it (which spends a code to buy "
              "nothing you do not already have).")
        report_coverage(body.get("token_expires"))
        return 0

    print("\nOpen TCInvest -> Smart OTP (iOTP) and read the 6-digit code.")
    print("One code mints ONE token good for ~8 hours and every data call "
          "afterwards needs\nno OTP at all. One attempt will be made: nothing "
          "here retries.\n")
    otp = prompt_otp()
    if otp is None:
        return 1

    print("\n  exchanging (one attempt, no retry)...")
    code, body = call("POST", gateway + PRIME_PATH, bearer, {"otp": otp})
    del otp                                    # not kept, not logged, not echoed
    if code != 200:
        print(f"  FAILED — HTTP {code}: "
              f"{json.dumps(body, ensure_ascii=False)[:400]}")
        print("\n  Not retried, on purpose. If the code had simply expired, "
              "re-run this script\n  with a fresh one. If the message names a "
              "limit or the key, read it before\n  spending another code — "
              "the daily exchange budget is unpublished.")
        return 1

    print(f"  OK — token stored in Redis, expires "
          f"{fmt_expiry(body.get('token_expires'))}")
    report_coverage(body.get("token_expires"))
    print("\n  Verify any time with --status, or watch `needs_prime` on "
          "stock-data-service\n  /health; it turns true 10 minutes before the "
          "token actually dies.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
