"""The default-secret fail-fast: does the guard fire on what actually ships?

Tech Debt / Backlog #24. assert_no_placeholder_secrets has been wired into all
13 services since June and refuses to boot outside `development`. It had no
tests, and measured 2026-11-02 its placeholder list had fallen behind the
deployment it guards:

    docker-compose.full-stack.yml injects   caught before?
      JWT_SECRET_KEY  dev-secret-key-...      NO   <- the dangerous one
      DATABASE_PASSWORD  stockpass            NO   (only Mysql_2025 was listed)
      RABBITMQ_PASSWORD  stockpass            yes

So with no .env present, every service would have booted in ENVIRONMENT=production
signing JWTs with a secret committed to this repository, and the guard built to
stop exactly that would have passed it. A guard that cannot fire is worse than no
guard, because it is believed.

The last test here is the one that prevents a recurrence: it reads the compose
file and asserts the guard covers every default it injects for a required
secret, so the list cannot silently fall behind again.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from stock_common.secrets_validation import (
    REQUIRED_SECRET_FIELDS,
    WARN_ONLY_SECRET_FIELDS,
    assert_no_placeholder_secrets,
)


class _S:
    """A stand-in Settings object."""

    def __init__(self, environment="production", **fields):
        self.ENVIRONMENT = environment
        for k, v in fields.items():
            setattr(self, k, v)


def _ok(environment="production"):
    return _S(
        environment=environment,
        JWT_SECRET_KEY="62ee7697c3560fc19fac7fa5f52753d6cd",
        DATABASE_PASSWORD="a-real-password",
        RABBITMQ_PASSWORD="another-real-one",
    )


# ---------------------------------------------------------------------------
# the gap this work closed
# ---------------------------------------------------------------------------

def test_the_jwt_secret_that_compose_injects_is_refused():
    """The hole. `${JWT_SECRET_KEY:-dev-secret-key-change-in-production}` is what
    a deployment without a .env actually gets, and it was not on the list."""
    s = _ok()
    s.JWT_SECRET_KEY = "dev-secret-key-change-in-production"
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        assert_no_placeholder_secrets(s, service_name="svc")


def test_the_code_default_jwt_secret_is_still_refused():
    """The literal in every service's config.py. It was already caught and must
    stay caught — the fix adds values, it does not replace them."""
    s = _ok()
    s.JWT_SECRET_KEY = "your-secret-key-change-in-production"
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        assert_no_placeholder_secrets(s, service_name="svc")


def test_the_database_password_that_compose_injects_is_WARNED_not_refused(caplog):
    """The one deliberate exception, and it is not a weakening — it is a
    measurement.

    `stockpass` is the compose default for DATABASE_PASSWORD, and measured
    2026-11-02 it is ALSO the owner's real MySQL password: every running service
    has DATABASE_PASSWORD=stockpass with ENVIRONMENT=production, and .env sets
    MYSQL_PASSWORD=stockpass. Refusing it would not improve security, it would
    refuse to start all 13 services — an outage dressed as a fix. So it warns at
    every startup until the credential is rotated, at which point it moves into
    the refusing list. Tracked on Backlog #24.
    """
    import logging

    s = _ok()
    s.DATABASE_PASSWORD = "stockpass"
    with caplog.at_level(logging.WARNING):
        assert_no_placeholder_secrets(s, service_name="svc")   # must NOT raise
    assert "DATABASE_PASSWORD" in caplog.text
    assert "rotate" in caplog.text.lower()


def test_the_mysql_root_default_is_still_refused():
    s = _ok()
    s.DATABASE_PASSWORD = "Mysql_2025"
    with pytest.raises(RuntimeError, match="DATABASE_PASSWORD"):
        assert_no_placeholder_secrets(s, service_name="svc")


def test_the_rabbitmq_default_is_refused():
    s = _ok()
    s.RABBITMQ_PASSWORD = "stockpass"
    with pytest.raises(RuntimeError, match="RABBITMQ_PASSWORD"):
        assert_no_placeholder_secrets(s, service_name="svc")


# ---------------------------------------------------------------------------
# an absent secret is worse than a default one
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("blank", ["", "   ", None])
def test_a_blank_required_secret_is_refused(blank):
    """An empty JWT secret is not 'unconfigured', it is a signing key of zero
    length. Previously only exact placeholder matches were caught, so a blank
    sailed through."""
    s = _ok()
    s.JWT_SECRET_KEY = blank
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        assert_no_placeholder_secrets(s, service_name="svc")


def test_an_optional_empty_secret_is_NOT_refused():
    """Counterpart, and the reason blankness is only checked on REQUIRED fields:
    compose ships ANTHROPIC_API_KEY, OPENAI_API_KEY, VNSTOCK_API_KEY and
    BROKER_MAIL_PASSWORD empty on purpose — those are optional features. Failing
    on them would refuse to boot a correctly configured stack."""
    s = _ok()
    s.ANTHROPIC_API_KEY = ""
    s.OPENAI_API_KEY = ""
    s.VNSTOCK_API_KEY = ""
    assert_no_placeholder_secrets(s, service_name="svc")   # must not raise


# ---------------------------------------------------------------------------
# behaviour that must not change
# ---------------------------------------------------------------------------

def test_development_is_a_no_op_so_a_local_stack_still_boots():
    """The whole point of the environment gate. A developer running the compose
    defaults must not be locked out."""
    s = _S(environment="development",
           JWT_SECRET_KEY="dev-secret-key-change-in-production",
           DATABASE_PASSWORD="stockpass",
           RABBITMQ_PASSWORD="stockpass")
    assert_no_placeholder_secrets(s, service_name="svc")   # must not raise


@pytest.mark.parametrize("env", ["production", "staging", "test", "PRODUCTION"])
def test_every_non_development_environment_enforces(env):
    s = _S(environment=env, JWT_SECRET_KEY="your-secret-key-change-in-production")
    with pytest.raises(RuntimeError):
        assert_no_placeholder_secrets(s, service_name="svc")


def test_real_secrets_pass():
    assert_no_placeholder_secrets(_ok(), service_name="svc")


def test_a_field_the_service_does_not_define_is_skipped():
    """Not every service has a database or a broker; a missing attribute is not
    a violation."""
    s = _S(environment="production", JWT_SECRET_KEY="a-real-secret")
    assert_no_placeholder_secrets(s, service_name="svc")


def test_the_error_names_the_service_and_every_offender():
    s = _S(environment="production",
           JWT_SECRET_KEY="dev-secret-key-change-in-production",
           DATABASE_PASSWORD="Mysql_2025",
           RABBITMQ_PASSWORD="stockpass")
    with pytest.raises(RuntimeError) as exc:
        assert_no_placeholder_secrets(s, service_name="auth-service")
    msg = str(exc.value)
    assert "auth-service" in msg
    for field in ("JWT_SECRET_KEY", "DATABASE_PASSWORD", "RABBITMQ_PASSWORD"):
        assert field in msg, msg


def test_extra_checks_still_work():
    """Services pass service-specific placeholders through this hook."""
    s = _ok()
    s.BROKER_MAIL_PASSWORD = "changeme"
    with pytest.raises(RuntimeError, match="BROKER_MAIL_PASSWORD"):
        assert_no_placeholder_secrets(
            s, service_name="svc",
            extra_checks=[("BROKER_MAIL_PASSWORD", "changeme")])


# ---------------------------------------------------------------------------
# the test that stops the list drifting behind the deployment again
# ---------------------------------------------------------------------------

#: compose variable -> the settings field the services read it as.
_COMPOSE_TO_FIELD = {
    "JWT_SECRET_KEY": "JWT_SECRET_KEY",
    "MYSQL_PASSWORD": "DATABASE_PASSWORD",      # DATABASE_PASSWORD=${MYSQL_PASSWORD:-...}
    "MYSQL_ROOT_PASSWORD": "DATABASE_PASSWORD",
    "RABBITMQ_PASSWORD": "RABBITMQ_PASSWORD",
}


def _compose_defaults():
    root = pathlib.Path(__file__).resolve().parents[2].parent
    compose = root / "docker-compose.full-stack.yml"
    if not compose.is_file():
        pytest.skip(f"compose file not found at {compose}")
    found = {}
    for var, default in re.findall(r"\$\{([A-Z_]+):-([^}]*)\}", compose.read_text()):
        if var in _COMPOSE_TO_FIELD and default:
            found.setdefault(_COMPOSE_TO_FIELD[var], set()).add(default)
    return found


def test_every_secret_default_compose_injects_is_on_the_list():
    """THE REGRESSION GUARD FOR THIS WHOLE ITEM.

    The guard existed, was wired into 13 services, and could not fire on the
    value the deployment actually supplied — because the list was written
    against the code defaults and compose injects different ones. Reading the
    compose file here means the two cannot diverge silently: add a new
    `${SECRET:-default}` and this fails until the guard knows about it.
    """
    defaults = _compose_defaults()
    assert defaults, "parsed no secret defaults from compose — the regex has rotted"
    missing = [
        (field, value)
        for field, values in defaults.items()
        for value in values
        if value not in REQUIRED_SECRET_FIELDS.get(field, set())
        and value not in WARN_ONLY_SECRET_FIELDS.get(field, set())
    ]
    assert not missing, (
        "docker-compose injects secret defaults the guard neither refuses nor "
        "warns about: " + ", ".join(f"{f}={v!r}" for f, v in missing)
    )


def test_the_only_tolerated_default_is_the_one_still_in_real_use():
    """Guards the exception itself. WARN_ONLY is a measured, temporary carve-out,
    not a place to quietly park anything inconvenient — if it grows, that should
    require saying so here."""
    assert WARN_ONLY_SECRET_FIELDS == {"DATABASE_PASSWORD": frozenset({"stockpass"})}


def test_a_warn_only_value_is_not_also_on_the_refusing_list():
    """Belt and braces: a value in both would refuse while claiming to warn."""
    for field, values in WARN_ONLY_SECRET_FIELDS.items():
        assert not (values & REQUIRED_SECRET_FIELDS.get(field, frozenset())), field
