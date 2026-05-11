"""Direct tests for UserRepository.

These exercise the SQL methods against the in-memory SQLite test_db
fixture (no mocks) — covering the methods that aren't routinely hit by
the route-level tests: update_user, update_password, update_last_login,
verify_user, deactivate_user, get_all_users, refresh-token CRUD,
cleanup_expired_tokens, get_user_active_tokens.
"""
from datetime import datetime, timedelta

import pytest

from app.models.domain import RefreshToken, User, UserRole
from app.repositories.user_repository import UserRepository


async def _seed_user(repo: UserRepository, *, email="alice@example.com",
                     username="alice", full_name="Alice Liddell") -> User:
    return await repo.create_user(
        email=email,
        username=username,
        hashed_password="hashed",
        full_name=full_name,
    )


# ---------------------------------------------------------------------------
# create_user — full_name splitting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_user_splits_full_name_into_first_and_last(test_db):
    repo = UserRepository(test_db)
    user = await _seed_user(repo, full_name="Alice Liddell")
    assert user.first_name == "Alice"
    assert user.last_name == "Liddell"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_create_user_handles_single_word_name(test_db):
    repo = UserRepository(test_db)
    user = await _seed_user(repo, email="cher@example.com", username="cher", full_name="Cher")
    assert user.first_name == "Cher"
    assert user.last_name is None


@pytest.mark.asyncio
async def test_create_user_handles_no_full_name(test_db):
    repo = UserRepository(test_db)
    user = await repo.create_user(
        email="x@example.com",
        username="x",
        hashed_password="h",
        full_name=None,
    )
    assert user.first_name is None
    assert user.last_name is None


# ---------------------------------------------------------------------------
# get_user_by_* lookups
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_by_email_returns_user(test_db):
    repo = UserRepository(test_db)
    seeded = await _seed_user(repo)
    found = await repo.get_user_by_email("alice@example.com")
    assert found is not None
    assert found.id == seeded.id


@pytest.mark.asyncio
async def test_get_user_by_email_returns_none_when_missing(test_db):
    repo = UserRepository(test_db)
    assert await repo.get_user_by_email("nobody@example.com") is None


@pytest.mark.asyncio
async def test_get_user_by_username_returns_user(test_db):
    repo = UserRepository(test_db)
    seeded = await _seed_user(repo)
    found = await repo.get_user_by_username("alice")
    assert found is not None
    assert found.id == seeded.id


# ---------------------------------------------------------------------------
# update_user / update_password / update_last_login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_user_persists_arbitrary_fields(test_db):
    repo = UserRepository(test_db)
    seeded = await _seed_user(repo)
    updated = await repo.update_user(seeded.id, first_name="Updated")
    assert updated is not None
    assert updated.first_name == "Updated"


@pytest.mark.asyncio
async def test_update_password_returns_true_on_success(test_db):
    repo = UserRepository(test_db)
    seeded = await _seed_user(repo)
    ok = await repo.update_password(seeded.id, "new_hash")
    assert ok is True
    refreshed = await repo.get_user_by_id(seeded.id)
    # hashed_password property reads password_hash.
    assert refreshed.hashed_password == "new_hash"


@pytest.mark.asyncio
async def test_update_password_returns_false_when_no_rows_affected(test_db):
    repo = UserRepository(test_db)
    ok = await repo.update_password(999_999, "h")
    assert ok is False


@pytest.mark.asyncio
async def test_update_last_login_stamps_timestamp(test_db):
    repo = UserRepository(test_db)
    seeded = await _seed_user(repo)
    assert seeded.last_login is None
    await repo.update_last_login(seeded.id)
    refreshed = await repo.get_user_by_id(seeded.id)
    assert refreshed.last_login is not None
    assert (datetime.utcnow() - refreshed.last_login).total_seconds() < 60


# ---------------------------------------------------------------------------
# verify_user / deactivate_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_user_returns_true_for_compatibility(test_db):
    """The schema doesn't have is_verified; the method is a no-op
    returning True so legacy callers don't break."""
    repo = UserRepository(test_db)
    assert await repo.verify_user(1) is True


@pytest.mark.asyncio
async def test_deactivate_user_marks_is_active_false(test_db):
    repo = UserRepository(test_db)
    seeded = await _seed_user(repo)
    ok = await repo.deactivate_user(seeded.id)
    assert ok is True
    refreshed = await repo.get_user_by_id(seeded.id)
    assert refreshed.is_active is False


@pytest.mark.asyncio
async def test_deactivate_user_returns_false_when_missing(test_db):
    repo = UserRepository(test_db)
    assert await repo.deactivate_user(999_999) is False


# ---------------------------------------------------------------------------
# get_all_users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_users_returns_paginated_rows(test_db):
    repo = UserRepository(test_db)
    for i in range(5):
        await _seed_user(repo, email=f"u{i}@example.com", username=f"u{i}")

    page1 = await repo.get_all_users(skip=0, limit=3)
    assert len(page1) == 3

    page2 = await repo.get_all_users(skip=3, limit=3)
    assert len(page2) == 2  # 5 - 3 = 2 remaining


# ---------------------------------------------------------------------------
# Refresh token CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_refresh_token_persists_with_metadata(test_db):
    repo = UserRepository(test_db)
    user = await _seed_user(repo)
    expires = datetime.utcnow() + timedelta(days=7)

    token = await repo.create_refresh_token(
        user.id, "tok-abc", expires, user_agent="ua", ip_address="1.1.1.1"
    )
    assert token.id is not None
    assert token.token == "tok-abc"
    assert token.user_agent == "ua"
    assert token.ip_address == "1.1.1.1"
    assert token.is_revoked is False


@pytest.mark.asyncio
async def test_get_refresh_token_returns_row(test_db):
    repo = UserRepository(test_db)
    user = await _seed_user(repo)
    expires = datetime.utcnow() + timedelta(days=7)
    await repo.create_refresh_token(user.id, "tok-1", expires)

    found = await repo.get_refresh_token("tok-1")
    assert found is not None
    assert found.user_id == user.id


@pytest.mark.asyncio
async def test_get_refresh_token_returns_none_when_unknown(test_db):
    repo = UserRepository(test_db)
    assert await repo.get_refresh_token("never-issued") is None


@pytest.mark.asyncio
async def test_revoke_refresh_token_marks_revoked(test_db):
    repo = UserRepository(test_db)
    user = await _seed_user(repo)
    expires = datetime.utcnow() + timedelta(days=7)
    await repo.create_refresh_token(user.id, "tok-1", expires)

    ok = await repo.revoke_refresh_token("tok-1")
    assert ok is True
    found = await repo.get_refresh_token("tok-1")
    assert found.is_revoked is True
    assert found.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_refresh_token_returns_false_when_unknown(test_db):
    repo = UserRepository(test_db)
    assert await repo.revoke_refresh_token("never-issued") is False


@pytest.mark.asyncio
async def test_revoke_all_user_tokens_revokes_only_active_for_that_user(test_db):
    repo = UserRepository(test_db)
    alice = await _seed_user(repo)
    bob = await _seed_user(repo, email="bob@example.com", username="bob")
    expires = datetime.utcnow() + timedelta(days=7)

    await repo.create_refresh_token(alice.id, "a1", expires)
    await repo.create_refresh_token(alice.id, "a2", expires)
    await repo.create_refresh_token(bob.id, "b1", expires)
    # Pre-revoke a3 so it shouldn't be touched again.
    await repo.create_refresh_token(alice.id, "a3", expires)
    await repo.revoke_refresh_token("a3")

    n = await repo.revoke_all_user_tokens(alice.id)
    # a1 + a2 revoked; a3 was already revoked and excluded.
    assert n == 2

    # Bob's token unchanged.
    bobs_tok = await repo.get_refresh_token("b1")
    assert bobs_tok.is_revoked is False


# ---------------------------------------------------------------------------
# cleanup_expired_tokens
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleanup_expired_tokens_deletes_only_expired_rows(test_db):
    repo = UserRepository(test_db)
    user = await _seed_user(repo)

    past = datetime.utcnow() - timedelta(days=1)
    future = datetime.utcnow() + timedelta(days=1)

    await repo.create_refresh_token(user.id, "expired-1", past)
    await repo.create_refresh_token(user.id, "expired-2", past)
    await repo.create_refresh_token(user.id, "active-1", future)

    n = await repo.cleanup_expired_tokens()
    assert n == 2
    # The active one remains.
    assert (await repo.get_refresh_token("active-1")) is not None
    assert (await repo.get_refresh_token("expired-1")) is None


# ---------------------------------------------------------------------------
# get_user_active_tokens
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_active_tokens_filters_revoked_and_expired(test_db):
    repo = UserRepository(test_db)
    user = await _seed_user(repo)

    future = datetime.utcnow() + timedelta(days=7)
    past = datetime.utcnow() - timedelta(days=1)

    await repo.create_refresh_token(user.id, "active-1", future)
    await repo.create_refresh_token(user.id, "active-2", future)
    await repo.create_refresh_token(user.id, "expired", past)
    await repo.create_refresh_token(user.id, "revoked", future)
    await repo.revoke_refresh_token("revoked")

    active = await repo.get_user_active_tokens(user.id)
    tokens = {t.token for t in active}
    assert tokens == {"active-1", "active-2"}
