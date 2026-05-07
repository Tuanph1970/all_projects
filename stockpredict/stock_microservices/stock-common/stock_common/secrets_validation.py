"""Shared startup validator for known-bad placeholder secrets.

Each service's config.py calls `assert_no_placeholder_secrets()` at the end
of `get_settings()`. In non-development environments the call raises if any
of the known placeholder values are still present, refusing to boot rather
than silently shipping a known-weak credential.

Documented in SECURITY_AUDIT.md (HIGH #1, #2). The auth-service shipped
this pattern locally first; this module hoists it so every service uses the
same list.
"""
from __future__ import annotations

from typing import Iterable, Optional

# Known placeholders that ship in `pydantic-settings` defaults across the
# stockpredict services. Any service still using these in production has
# clearly skipped env-var configuration.
_PLACEHOLDER_VALUES: dict[str, str] = {
    "JWT_SECRET_KEY": "your-secret-key-change-in-production",
    "DATABASE_PASSWORD": "Mysql_2025",
    "RABBITMQ_PASSWORD": "stockpass",
}


def assert_no_placeholder_secrets(
    settings_obj: object,
    *,
    service_name: str,
    extra_checks: Optional[Iterable[tuple[str, str]]] = None,
) -> None:
    """Raise RuntimeError if any known placeholder secret is still set.

    No-op in development. In any other ENVIRONMENT (staging, production,
    test) it inspects the well-known field names on `settings_obj` and
    fails loudly so deployments don't silently ship default credentials.

    Args:
        settings_obj: a Settings instance (must expose ENVIRONMENT plus
            whichever secret fields the service uses).
        service_name: shown in the error message.
        extra_checks: optional list of (attribute_name, placeholder_value)
            for service-specific secrets beyond the shared defaults.
    """
    env = getattr(settings_obj, "ENVIRONMENT", None) or getattr(settings_obj, "environment", "")
    if str(env).lower() == "development":
        return

    problems: list[str] = []
    for field, placeholder in _PLACEHOLDER_VALUES.items():
        if not hasattr(settings_obj, field):
            continue
        actual = getattr(settings_obj, field, None)
        if actual == placeholder:
            problems.append(f"{field} is unset (still the default placeholder)")

    for field, placeholder in (extra_checks or ()):
        actual = getattr(settings_obj, field, None)
        if actual == placeholder:
            problems.append(f"{field} is unset (still the default placeholder)")

    if problems:
        raise RuntimeError(
            f"{service_name} refuses to start with default secrets in environment "
            f"'{env}'. Set the env vars: " + ", ".join(problems)
        )
