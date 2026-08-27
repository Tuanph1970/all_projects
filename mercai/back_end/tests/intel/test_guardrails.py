"""
The flag/quota/hash machinery, which is now the whole of the intel service's
shared logic.

These were never tested before -- tests/ai/ mocked `check_quota` and
`consume_quota` out rather than exercising them, so the fail-open behaviour
that protects sellers during a Redis outage was asserted nowhere. It is
asserted here, because price intelligence relies on it.
"""
import pytest

from shared.config import settings


# --------------------------------------------------------------------------
# Feature flags
# --------------------------------------------------------------------------

def test_flag_off_means_off(intel, monkeypatch, fake_redis):
    monkeypatch.setattr(settings, "INTEL_PRICE_ENABLED", False)
    assert intel.feature_enabled("price_intel") is False


def test_flag_on_with_no_allowlist_means_everyone(intel, monkeypatch, fake_redis):
    """
    An EMPTY allowlist means "everyone", not "no one".

    The opposite reading makes flipping the global flag appear to do nothing,
    which invites someone to delete the check entirely.
    """
    monkeypatch.setattr(settings, "INTEL_PRICE_ENABLED", True)
    fake_redis(None)
    assert intel.feature_enabled("price_intel", seller_id=7) is True


def test_unknown_feature_is_never_enabled(intel, monkeypatch, fake_redis):
    monkeypatch.setattr(settings, "INTEL_PRICE_ENABLED", True)
    assert intel.feature_enabled("listing_optimizer", seller_id=7) is False
    assert intel.feature_enabled("chat_copilot") is False


def test_allowlist_gates_individual_sellers(intel, monkeypatch, fake_redis):
    monkeypatch.setattr(settings, "INTEL_PRICE_ENABLED", True)

    class FakeRedis:
        def exists(self, key):
            return 1

        def sismember(self, key, member):
            return member == "7"

    fake_redis(FakeRedis())
    assert intel.feature_enabled("price_intel", seller_id=7) is True
    assert intel.feature_enabled("price_intel", seller_id=8) is False


def test_allowlist_failure_falls_back_to_the_global_flag(intel, monkeypatch, fake_redis):
    """A Redis fault must not silently disable a feature that is switched on."""
    monkeypatch.setattr(settings, "INTEL_PRICE_ENABLED", True)

    class BrokenRedis:
        def exists(self, key):
            raise RuntimeError("redis is down")

    fake_redis(BrokenRedis())
    assert intel.feature_enabled("price_intel", seller_id=7) is True


# --------------------------------------------------------------------------
# Quotas
# --------------------------------------------------------------------------

def test_quota_fails_open_when_redis_is_absent(intel, monkeypatch, fake_redis):
    """
    A cache outage should degrade cost control, not block sellers.

    This is the assertion that was missing entirely before.
    """
    fake_redis(None)
    assert intel.check_quota("price_intel", 7) == (True, None)


def test_quota_blocks_when_the_hourly_limit_is_reached(intel, monkeypatch, fake_redis):
    class FakeRedis:
        def get(self, key):
            return settings.AI_QUOTA_PER_HOUR if key.endswith(":h") else 0

        def ttl(self, key):
            return 1800

    fake_redis(FakeRedis())
    allowed, retry_after = intel.check_quota("price_intel", 7)
    assert allowed is False
    assert retry_after == 1800


def test_quota_blocks_when_the_daily_limit_is_reached(intel, monkeypatch, fake_redis):
    class FakeRedis:
        def get(self, key):
            return 0 if key.endswith(":h") else settings.AI_QUOTA_PER_DAY

        def ttl(self, key):
            return 60_000

    fake_redis(FakeRedis())
    allowed, retry_after = intel.check_quota("price_intel", 7)
    assert allowed is False
    assert retry_after == 60_000


def test_consume_quota_sets_a_ttl_only_on_first_increment(intel, monkeypatch, fake_redis):
    """Without the guard, a busy seller's counter would never expire."""
    expires = []

    class FakeRedis:
        def __init__(self):
            self.counts = {}

        def incr(self, key):
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        def expire(self, key, ttl):
            expires.append((key, ttl))

    fake_redis(FakeRedis())
    intel.consume_quota("price_intel", 7)
    intel.consume_quota("price_intel", 7)

    assert len(expires) == 2, "one TTL per key, set on the first increment only"
    assert sorted(ttl for _, ttl in expires) == [3600, 86400]


def test_quota_failure_allows_the_request(intel, monkeypatch, fake_redis):
    class BrokenRedis:
        def get(self, key):
            raise RuntimeError("redis is down")

    fake_redis(BrokenRedis())
    assert intel.check_quota("price_intel", 7) == (True, None)


# --------------------------------------------------------------------------
# Input hashing
# --------------------------------------------------------------------------

def test_hash_is_stable_across_key_order(intel):
    a = intel.input_hash({"b": 2, "a": 1}, "v1", "rules")
    b = intel.input_hash({"a": 1, "b": 2}, "v1", "rules")
    assert a == b


def test_hash_changes_with_the_ruleset_version(intel):
    """
    Shipping a new ruleset must invalidate every cached entry.

    Otherwise a fixed extraction bug keeps serving its old wrong answer from
    cache, which is the failure mode this field exists to prevent.
    """
    a = intel.input_hash({"url": "x"}, "v1", "rules")
    b = intel.input_hash({"url": "x"}, "v2", "rules")
    assert a != b


def test_hash_survives_values_json_cannot_encode(intel):
    """Decimals and dates reach this from SQLAlchemy rows; it must not raise."""
    from datetime import date
    from decimal import Decimal

    digest = intel.input_hash(
        {"price": Decimal("185000.00"), "seen": date(2026, 8, 27)}, "v1", "rules"
    )
    assert len(digest) == 64
