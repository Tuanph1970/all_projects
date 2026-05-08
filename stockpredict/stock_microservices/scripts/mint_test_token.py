#!/usr/bin/env python3
"""Mint a short-lived JWT for the perf baseline runner.

Reads JWT_SECRET_KEY from the environment (matching the auth-service
config). Defaults to a 1-hour token for sub=1 / role=user, which is
plenty for a perf sweep.

Usage:
    JWT_SECRET_KEY=... ./scripts/mint_test_token.py
    TOKEN=$(JWT_SECRET_KEY=... ./scripts/mint_test_token.py) \\
        ./scripts/perf_baseline.sh
"""
import os
import sys
from datetime import datetime, timedelta

try:
    import jwt  # PyJWT
except ImportError:
    print("PyJWT not installed; pip install PyJWT", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        print(
            "JWT_SECRET_KEY env var required. Get it from your local .env or "
            "auth-service config.",
            file=sys.stderr,
        )
        return 2

    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    user_id = os.environ.get("PERF_USER_ID", "1")
    expires_minutes = int(os.environ.get("PERF_TOKEN_TTL_MIN", "60"))

    payload = {
        "sub": str(user_id),
        "email": "perf@example.com",
        "role": os.environ.get("PERF_USER_ROLE", "user"),
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
    }
    print(jwt.encode(payload, secret, algorithm=algorithm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
