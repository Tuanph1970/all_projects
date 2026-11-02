"""Shared startup validator for known-bad placeholder secrets.

Each service's config.py calls `assert_no_placeholder_secrets()` at the end of
`get_settings()`. In non-development environments the call raises if any known
placeholder is still present, refusing to boot rather than silently shipping a
known-weak credential.

Documented in SECURITY_AUDIT.md (HIGH #1, #2). The auth-service shipped this
pattern locally first; this module hoists it so every service uses the same list.

WHY EACH FIELD TAKES A SET, not one value (fixed 2026-11-02). The original list
held exactly one placeholder per field, written against the defaults in the
services' own `config.py`. But a deployment does not use those: docker-compose
injects its own via `${VAR:-default}`, and they are DIFFERENT strings. So with no
.env present every service booted in ENVIRONMENT=production signing JWTs with
`dev-secret-key-change-in-production` — a value committed to this repository —
and this guard, built to stop precisely that, accepted it. A guard that cannot
fire is worse than no guard, because it is believed.

`tests/test_secrets_validation.py` now reads docker-compose.full-stack.yml and
fails if it injects a secret default this module would accept, so the list
cannot fall behind the deployment again.
"""
from __future__ import annotations

import logging
from typing import Iterable, Mapping, Optional

logger = logging.getLogger(__name__)

#: Secrets that every deployment MUST set, and the placeholder values seen in
#: this repository — from the services' pydantic defaults AND from the compose
#: `${VAR:-default}` fallbacks, which are not the same strings. A few generic
#: values are included because they cost nothing and are what people type.
#:
#: These fields are also refused when BLANK: an empty JWT secret is not
#: "unconfigured", it is a signing key of zero length.
REQUIRED_SECRET_FIELDS: dict[str, frozenset[str]] = {
    "JWT_SECRET_KEY": frozenset({
        "your-secret-key-change-in-production",   # services/*/app/config.py
        "dev-secret-key-change-in-production",    # docker-compose.full-stack.yml
        "change-me-in-production",                # stock_common.config JWTConfig
        "changeme", "secret", "test-secret-key",
    }),
    "DATABASE_PASSWORD": frozenset({
        "Mysql_2025",      # ${MYSQL_ROOT_PASSWORD:-Mysql_2025}
        "password", "root", "changeme",
        # NOTE: "stockpass" is deliberately NOT here. See
        # WARN_ONLY_SECRET_FIELDS below — it is the owner's real MySQL password
        # today, so refusing it would refuse to start every service.
    }),
    "RABBITMQ_PASSWORD": frozenset({
        "stockpass",       # ${RABBITMQ_PASSWORD:-stockpass}
        "guest",           # stock_common.config RabbitMQConfig
        "password", "changeme",
    }),
}

#: Placeholders that are STILL IN LEGITIMATE USE and therefore warn rather than
#: refuse. Measured 2026-11-02: every running service has
#: DATABASE_PASSWORD=stockpass with ENVIRONMENT=production, and the owner's .env
#: sets MYSQL_PASSWORD=stockpass — so this compose default is also the real
#: credential. Promoting it to REQUIRED_SECRET_FIELDS would refuse to start all
#: 13 services on the next deploy, which is not a security improvement, it is an
#: outage.
#:
#: THE FIX IS A ROTATION, NOT A CODE CHANGE: set MYSQL_PASSWORD in .env to
#: something not in this file, recreate the MySQL user with it, then move
#: "stockpass" up into REQUIRED_SECRET_FIELDS and delete it here. Tracked as an
#: owner decision on Backlog #24. Until then the value is reported at every
#: startup so it cannot be forgotten.
WARN_ONLY_SECRET_FIELDS: dict[str, frozenset[str]] = {
    "DATABASE_PASSWORD": frozenset({"stockpass"}),
}

#: Environments in which a placeholder is tolerated. Only development: a
#: developer running the compose defaults must not be locked out of their own
#: machine, which is the whole reason this is gated rather than absolute.
_PERMISSIVE_ENVIRONMENTS = frozenset({"development", "dev", "local"})


def find_placeholder_secrets(
    settings_obj: object,
    *,
    required: Optional[Mapping[str, Iterable[str]]] = None,
    extra_checks: Optional[Iterable[tuple[str, str]]] = None,
) -> list[str]:
    """Every problem found, as human-readable strings. Pure; raises nothing.

    A field the object does not define is skipped — not every service has a
    database or a broker, and a missing attribute is not a violation.
    """
    problems: list[str] = []
    for field, placeholders in (required or REQUIRED_SECRET_FIELDS).items():
        if not hasattr(settings_obj, field):
            continue
        actual = getattr(settings_obj, field, None)
        if actual is None or not str(actual).strip():
            problems.append(f"{field} is blank")
        elif str(actual) in set(placeholders):
            problems.append(f"{field} is unset (still the default placeholder)")

    # Optional, service-specific secrets: an exact match only. Blankness is NOT
    # checked here, because compose deliberately ships ANTHROPIC_API_KEY,
    # OPENAI_API_KEY, VNSTOCK_API_KEY and BROKER_MAIL_PASSWORD empty — those
    # gate optional features, and refusing to boot over them would break a
    # correctly configured stack.
    for field, placeholder in (extra_checks or ()):
        if getattr(settings_obj, field, None) == placeholder:
            problems.append(f"{field} is unset (still the default placeholder)")
    return problems


def find_warn_only_secrets(settings_obj: object) -> list[str]:
    """Placeholders that are reported but tolerated (WARN_ONLY_SECRET_FIELDS)."""
    out: list[str] = []
    for field, placeholders in WARN_ONLY_SECRET_FIELDS.items():
        if not hasattr(settings_obj, field):
            continue
        if str(getattr(settings_obj, field, "")) in set(placeholders):
            out.append(f"{field} is a known default value")
    return out


def assert_no_placeholder_secrets(
    settings_obj: object,
    *,
    service_name: str,
    extra_checks: Optional[Iterable[tuple[str, str]]] = None,
) -> None:
    """Raise RuntimeError if any known placeholder or blank secret is set.

    No-op in development (see _PERMISSIVE_ENVIRONMENTS). In any other
    ENVIRONMENT — staging, production, test — it fails loudly so a deployment
    cannot silently ship default credentials.

    Args:
        settings_obj: a Settings instance exposing ENVIRONMENT plus whichever
            secret fields the service uses.
        service_name: shown in the error message.
        extra_checks: optional (attribute_name, placeholder_value) pairs for
            service-specific secrets beyond the shared list.
    """
    env = getattr(settings_obj, "ENVIRONMENT", None) or getattr(settings_obj, "environment", "")
    if str(env).strip().lower() in _PERMISSIVE_ENVIRONMENTS:
        problems = find_placeholder_secrets(settings_obj, extra_checks=extra_checks)
        if problems:
            # Said out loud even when tolerated: this is the configuration that
            # would refuse to boot the moment ENVIRONMENT stops being development.
            logger.warning(
                "%s is using default secrets (allowed in environment '%s', but it "
                "would refuse to start anywhere else): %s",
                service_name, env, ", ".join(problems),
            )
        return

    tolerated = find_warn_only_secrets(settings_obj)
    if tolerated:
        logger.warning(
            "%s is running with known default credentials in environment '%s': %s. "
            "These are tolerated only because they are currently the real values "
            "(see WARN_ONLY_SECRET_FIELDS); rotate them and promote them to the "
            "refusing list.", service_name, env, ", ".join(tolerated),
        )

    problems = find_placeholder_secrets(settings_obj, extra_checks=extra_checks)
    if problems:
        raise RuntimeError(
            f"{service_name} refuses to start with default secrets in environment "
            f"'{env}'. Set the env vars: " + ", ".join(problems)
        )
