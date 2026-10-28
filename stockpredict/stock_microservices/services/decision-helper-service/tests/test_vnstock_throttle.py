"""Backlog #49 — the vnstock call spacing, and the tier it comes from.

Tested because the two history-dump scripts are the slowest thing in the EM-3
and EM-4 workstreams (#86, #90 and #101 each spent roughly an hour of
wall-clock on pulls) and they previously hardcoded 3.2s, so a key bought them
nothing. A wrong value here is either an hour of waiting or a quota breach,
and neither announces itself.
"""
from __future__ import annotations

import os

import pytest

from tests.vnstock_throttle import (
    GUEST_INTERVAL_SECONDS,
    KEYED_INTERVAL_SECONDS,
    describe,
    has_api_key,
    min_interval,
)


def test_the_two_intervals_sit_just_under_their_quotas():
    """Pinned against the installed packages, which disagree with each other.

    Container (vnstock 4.0.7, tiered): guest {"min": 20}, free {"min": 60}.
    Host (vnstock 3.3.1, kept by owner decision): a flat VCI {"min": 60} with
    no tiers at all — so on the host the 3.1s "guest" interval is simply
    conservative, not required.

    Either way each interval must sit slightly ABOVE 60/limit, never below.
    """
    assert GUEST_INTERVAL_SECONDS > 60 / 20
    assert KEYED_INTERVAL_SECONDS > 60 / 60
    # ...and not so far above that the headroom is wasted.
    assert GUEST_INTERVAL_SECONDS < 3.5
    assert KEYED_INTERVAL_SECONDS < 1.3


def test_these_match_stock_data_services_rule():
    """The sibling copy. `Settings.vnstock_min_interval` in stock-data-service
    returns 1.05 with a key and 3.1 without; a service cannot import another
    service's config, so the numbers are restated in `vnstock_throttle` and
    pinned here. If that rule changes, this test is the reminder that this
    copy exists."""
    assert GUEST_INTERVAL_SECONDS == pytest.approx(3.1)
    assert KEYED_INTERVAL_SECONDS == pytest.approx(1.05)


def test_no_key_is_the_guest_interval():
    assert min_interval({}) == pytest.approx(GUEST_INTERVAL_SECONDS)
    assert has_api_key({}) is False


def test_a_key_raises_the_rate():
    env = {"VNSTOCK_API_KEY": "a-real-community-key"}
    assert has_api_key(env) is True
    assert min_interval(env) == pytest.approx(KEYED_INTERVAL_SECONDS)


@pytest.mark.parametrize("blank", ["", " ", "\t", "\n  "])
def test_a_blank_key_counts_as_GUEST_not_as_a_key(blank):
    """docker-compose passes `${VNSTOCK_API_KEY:-}` through as "".

    Treating that as a key would silently triple a guest's call rate and
    breach the quota — the same trap stock-data-service's `_blank_env_is_unset`
    validator exists to close. The one case most likely to occur in
    production, since the variable ships declared-but-empty in `.env`.
    """
    env = {"VNSTOCK_API_KEY": blank}
    assert has_api_key(env) is False
    assert min_interval(env) == pytest.approx(GUEST_INTERVAL_SECONDS)


def test_an_explicit_override_wins_over_the_tier():
    assert min_interval({"VNSTOCK_MIN_INTERVAL_SECONDS": "0.5"}) == pytest.approx(0.5)
    assert min_interval({
        "VNSTOCK_API_KEY": "k", "VNSTOCK_MIN_INTERVAL_SECONDS": "7",
    }) == pytest.approx(7.0)


@pytest.mark.parametrize("junk", ["abc", "", "   ", "1.0.0"])
def test_an_unparseable_override_falls_back_to_the_tier_not_to_zero(junk):
    """A typo must not become `sleep(0)` and a quota ban."""
    env = {"VNSTOCK_MIN_INTERVAL_SECONDS": junk}
    assert min_interval(env) == pytest.approx(GUEST_INTERVAL_SECONDS)
    env["VNSTOCK_API_KEY"] = "k"
    assert min_interval(env) == pytest.approx(KEYED_INTERVAL_SECONDS)


def test_the_banner_names_the_tier_and_the_remedy():
    guest = describe({})
    assert "GUEST" in guest and "3.10s" in guest and "VNSTOCK_API_KEY" in guest
    keyed = describe({"VNSTOCK_API_KEY": "k"})
    assert "60 req/min" in keyed and "1.05s" in keyed
    # The hint must NOT appear once a key is set, or it reads as broken.
    assert "go ~3x faster" not in keyed


def test_the_banner_names_an_override_instead_of_nagging_about_the_key():
    line = describe({"VNSTOCK_MIN_INTERVAL_SECONDS": "0.5"})
    assert "0.50s" in line
    assert "override in force" in line
    assert "go ~3x faster" not in line


def test_the_interval_is_read_at_call_time_not_bound_at_import(monkeypatch):
    """The bound-default guard. This project has paid for that trap six times
    (EM-1 S2, #78, W1, #84, #85's MAX_SYMBOLS, #101's own default), and the
    dump scripts call `min_interval()` per iteration precisely so a key picked
    up mid-session takes effect.

    The `.env` fallback is stubbed out, not just the environment variables:
    this machine has a key installed in the repo `.env`, so clearing the env
    alone would still resolve to the keyed interval and the test would assert
    nothing. Found by this test failing the moment the fallback shipped.
    """
    from tests import vnstock_throttle

    monkeypatch.setattr(vnstock_throttle, "env_file_values", lambda: {})
    monkeypatch.delenv("VNSTOCK_API_KEY", raising=False)
    monkeypatch.delenv("VNSTOCK_MIN_INTERVAL_SECONDS", raising=False)
    assert min_interval() == pytest.approx(GUEST_INTERVAL_SECONDS)
    monkeypatch.setenv("VNSTOCK_API_KEY", "set-after-import")
    assert min_interval() == pytest.approx(KEYED_INTERVAL_SECONDS)


def test_the_dump_scripts_no_longer_hardcode_a_spacing():
    """The actual #49 defect: both scripts had `SPACING_SECONDS = 3.2`, so
    setting a key changed nothing for the slowest jobs in the project."""
    import inspect

    from tests import deep_history_dump, index_history_dump

    for module in (deep_history_dump, index_history_dump):
        source = inspect.getsource(module)
        assert "SPACING_SECONDS" not in source, module.__name__
        assert "min_interval()" in source, module.__name__


# ---------------------------------------------------------------------------
# The .env fallback for host-run scripts
# ---------------------------------------------------------------------------

def test_an_explicit_env_never_consults_the_dotenv_file():
    """Hermeticity, and it is why `_resolve` takes `env` at all.

    This machine's real `.env` has a key installed. If an explicit `env`
    argument fell through to the file, every test above asserting GUEST
    behaviour would flip to keyed on a configured machine and stay green on an
    unconfigured one — a suite whose result depends on local configuration.
    """
    from tests.vnstock_throttle import env_file_values

    assert min_interval({}) == pytest.approx(GUEST_INTERVAL_SECONDS)
    assert has_api_key({}) is False
    # ...even though the file itself may well have one.
    if env_file_values().get("VNSTOCK_API_KEY"):
        assert min_interval() == pytest.approx(KEYED_INTERVAL_SECONDS)


def test_the_dotenv_file_is_read_only_for_the_two_vnstock_names():
    """A dev helper has no business parsing a secrets file wholesale."""
    from tests.vnstock_throttle import _ENV_FILE_KEYS, env_file_values

    assert set(env_file_values()) <= set(_ENV_FILE_KEYS)
    assert _ENV_FILE_KEYS == ("VNSTOCK_API_KEY", "VNSTOCK_MIN_INTERVAL_SECONDS")


def test_a_real_environment_variable_beats_the_file(monkeypatch):
    """So a shell export can still override, e.g. to run deliberately gentler."""
    monkeypatch.setenv("VNSTOCK_MIN_INTERVAL_SECONDS", "9.5")
    assert min_interval() == pytest.approx(9.5)


def test_the_repo_dotenv_is_located_by_the_compose_file_beside_it():
    """Anchored on docker-compose.full-stack.yml rather than a parent count, so
    moving this file deeper does not silently start reading the wrong .env."""
    from tests.vnstock_throttle import _repo_env_file

    path = _repo_env_file()
    if path is not None:
        assert path.name == ".env"
        assert (path.parent / "docker-compose.full-stack.yml").exists()


def test_the_host_scripts_would_now_see_an_installed_key():
    """The defect this fallback fixes: the key lives in .env, which only
    docker-compose reads, so a dump started by hand saw GUEST forever. Skips
    when no key is installed, so CI without one stays green."""
    from tests.vnstock_throttle import env_file_values

    if not (env_file_values().get("VNSTOCK_API_KEY") or "").strip():
        pytest.skip("no VNSTOCK_API_KEY installed on this machine")
    assert min_interval() == pytest.approx(KEYED_INTERVAL_SECONDS)
    assert "60 req/min" in describe()


# ---------------------------------------------------------------------------
# activate() — the half I shipped missing
# ---------------------------------------------------------------------------

def test_activate_puts_the_key_where_vnai_will_find_it(monkeypatch):
    """The defect: reading .env for SPACING only.

    `vnai` grants the tier from `os.getenv("VNSTOCK_API_KEY")` itself. If the
    key never reaches `os.environ`, a host-run dump calls every 1.05s (~57
    req/min) while vnai still rate-limits it as a GUEST at 20 — a quota breach
    that ends in RateLimitExceeded partway through an hour-long pull.
    """
    from tests import vnstock_throttle

    monkeypatch.setattr(vnstock_throttle, "env_file_values",
                        lambda: {"VNSTOCK_API_KEY": "from-dot-env"})
    monkeypatch.delenv("VNSTOCK_API_KEY", raising=False)

    interval = vnstock_throttle.activate()

    assert os.environ["VNSTOCK_API_KEY"] == "from-dot-env"
    assert interval == pytest.approx(KEYED_INTERVAL_SECONDS)


def test_activate_does_not_overwrite_a_real_environment_variable(monkeypatch):
    """A shell export must still win over the file."""
    from tests import vnstock_throttle

    monkeypatch.setattr(vnstock_throttle, "env_file_values",
                        lambda: {"VNSTOCK_API_KEY": "from-dot-env"})
    monkeypatch.setenv("VNSTOCK_API_KEY", "from-the-shell")

    vnstock_throttle.activate()

    assert os.environ["VNSTOCK_API_KEY"] == "from-the-shell"


def test_activate_is_a_no_op_with_no_key_anywhere(monkeypatch):
    """No key must leave the environment untouched and stay on guest spacing —
    never set an empty variable, which vnai's presence check would still see
    as... nothing, but which would mislead anyone reading the environment."""
    from tests import vnstock_throttle

    monkeypatch.setattr(vnstock_throttle, "env_file_values", lambda: {})
    monkeypatch.delenv("VNSTOCK_API_KEY", raising=False)

    assert vnstock_throttle.activate() == pytest.approx(GUEST_INTERVAL_SECONDS)
    assert "VNSTOCK_API_KEY" not in os.environ


def test_both_dump_scripts_call_activate_before_pulling():
    """Wiring, asserted: the helper is useless if a script forgets it."""
    import inspect

    from tests import deep_history_dump, index_history_dump

    for module in (deep_history_dump, index_history_dump):
        source = inspect.getsource(module)
        assert "activate()" in source, module.__name__


def test_the_keyed_interval_respects_the_hosts_HOUR_cap_for_short_jobs():
    """The limit that is easy to miss: the host allows 3,000/hour = 50/min
    SUSTAINED, below the ~57/min that 1.05s implies. Fine for a 93-call dump
    (under two minutes) and not fine for a ~50-minute bulk job, which is why
    VNSTOCK_MIN_INTERVAL_SECONDS exists and is documented at 1.2 for those."""
    calls_per_minute = 60 / KEYED_INTERVAL_SECONDS
    assert calls_per_minute < 60                      # minute cap respected
    assert calls_per_minute > 3000 / 60               # ...but over the hour pace
    dump_calls = 93                                   # VNINDEX + 92 symbols
    assert dump_calls < 3000                          # so a dump cannot trip it
    assert min_interval({"VNSTOCK_MIN_INTERVAL_SECONDS": "1.2"}) == pytest.approx(1.2)
    assert 60 / 1.2 <= 3000 / 60                      # the documented long-job value
