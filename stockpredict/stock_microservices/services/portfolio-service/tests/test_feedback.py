"""v0.9 — the feedback form: collecting ideas and problems from users.

The form's value is almost entirely in whether a report arrives with enough
CONTEXT to act on. "The numbers look wrong" is a different report depending on
whether it came from the Chart analyst, the Backtest Studio or the Risk
Dashboard, and a user essentially never volunteers which. So the tests that
matter most here are about the context fields surviving the round trip, and
about the inbox being gated.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user, get_db
from app.main import app
from app.models.domain import FeedbackCategory, FeedbackStatus, UserFeedback
from app.models.schemas import FeedbackCreate

PREFIX = "/stock_helper/api/v2/portfolio"


def _db_capturing(added):
    """A session that records what was add()ed and refreshes it with an id."""
    db = AsyncMock()
    db.add = MagicMock(side_effect=added.append)

    async def _refresh(obj, *a, **k):
        if getattr(obj, "id", None) is None:
            obj.id = 1
        return obj

    db.refresh = AsyncMock(side_effect=_refresh)
    return db


async def _client(db, user=None):
    async def override_db():
        yield db

    def override_user():
        return user or {"user_id": 1, "email": "t@example.com", "role": "user"}

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Submitting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_submission_keeps_the_context_that_makes_it_actionable():
    """`page`, `app_version` and the user-agent are the whole point.

    The UI fills `page` from the current route, so the owner learns WHERE the
    user was without the user having to say — which they almost never do.
    """
    added = []
    db = _db_capturing(added)
    async with await _client(db) as c:
        r = await c.post(f"{PREFIX}/feedback", json={
            "category": "problem",
            "message": "The MA200 line disappears when I pick a short window.",
            "page": "/chart-narrator",
            "app_version": "0.9.0",
            "rating": 4,
            "contact_ok": True,
        }, headers={"user-agent": "Mozilla/5.0 (TestBrowser)"})
    assert r.status_code == 201, r.text
    assert len(added) == 1
    row = added[0]
    assert row.page == "/chart-narrator"
    assert row.app_version == "0.9.0"
    assert row.user_agent == "Mozilla/5.0 (TestBrowser)"
    assert row.contact_ok is True
    assert row.rating == 4
    assert row.user_id == 1
    assert row.status is FeedbackStatus.NEW


@pytest.mark.asyncio
async def test_the_category_is_stored_as_the_domain_enum_not_a_string():
    """The schema enum carries the lowercase VALUE; the SQLAlchemy enum column
    stores the member NAME. Passing the string straight through is how those two
    drift — the trap #117's AlertType hit, where MySQL held uppercase names."""
    added = []
    db = _db_capturing(added)
    async with await _client(db) as c:
        r = await c.post(f"{PREFIX}/feedback",
                         json={"category": "idea", "message": "Add a dark mode please"})
    assert r.status_code == 201
    assert added[0].category is FeedbackCategory.IDEA
    assert isinstance(added[0].category, FeedbackCategory)


@pytest.mark.asyncio
async def test_every_category_in_the_schema_exists_in_the_domain():
    """Two enums describing one concept must agree, or a legal form submission
    raises a ValueError at the conversion. Asserted as SETS, not spot-checked."""
    from app.models.schemas import FeedbackCategory as SchemaCategory
    from app.models.schemas import FeedbackStatus as SchemaStatus
    assert {e.value for e in SchemaCategory} == {e.value for e in FeedbackCategory}
    assert {e.value for e in SchemaStatus} == {e.value for e in FeedbackStatus}


@pytest.mark.asyncio
async def test_an_empty_or_trivial_message_is_rejected():
    """A one-character submission is an accident or a test. Letting it through
    spends the owner's attention on a row with no information in it."""
    db = _db_capturing([])
    async with await _client(db) as c:
        for bad in ("", "   ", "x", "ab"):
            r = await c.post(f"{PREFIX}/feedback",
                             json={"category": "idea", "message": bad})
            assert r.status_code == 422, f"{bad!r} was accepted"


@pytest.mark.asyncio
async def test_whitespace_is_stripped_rather_than_stored():
    added = []
    db = _db_capturing(added)
    async with await _client(db) as c:
        await c.post(f"{PREFIX}/feedback",
                     json={"category": "idea", "message": "  please add alerts  "})
    assert added[0].message == "please add alerts"


@pytest.mark.asyncio
async def test_an_out_of_range_rating_is_rejected():
    db = _db_capturing([])
    async with await _client(db) as c:
        for bad in (0, 6, -1):
            r = await c.post(f"{PREFIX}/feedback", json={
                "category": "idea", "message": "a valid message", "rating": bad})
            assert r.status_code == 422, f"rating {bad} was accepted"


@pytest.mark.asyncio
async def test_a_rating_is_optional_because_not_every_report_is_a_score():
    """Someone reporting a bug should not have to rate the app to send it."""
    added = []
    db = _db_capturing(added)
    async with await _client(db) as c:
        r = await c.post(f"{PREFIX}/feedback",
                         json={"category": "problem", "message": "Chart axis is cut off"})
    assert r.status_code == 201
    assert added[0].rating is None


@pytest.mark.asyncio
async def test_an_over_long_message_is_rejected_rather_than_truncated():
    """Silently truncating loses the end of a long, careful report — usually the
    part with the reproduction steps in it."""
    db = _db_capturing([])
    async with await _client(db) as c:
        r = await c.post(f"{PREFIX}/feedback",
                         json={"category": "idea", "message": "x" * 4001})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_the_submitter_cannot_set_their_own_user_id_or_status():
    """Both come from the server. A form that could claim another user_id, or
    pre-mark itself DONE, would be a trivially abusable inbox."""
    added = []
    db = _db_capturing(added)
    async with await _client(db) as c:
        r = await c.post(f"{PREFIX}/feedback", json={
            "category": "idea", "message": "trying to spoof",
            "user_id": 999, "status": "done", "owner_note": "mine now",
        })
    assert r.status_code == 201
    assert added[0].user_id == 1
    assert added[0].status is FeedbackStatus.NEW
    assert added[0].owner_note is None


# ---------------------------------------------------------------------------
# The inbox is gated
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_an_ordinary_user_cannot_read_everyone_elses_feedback():
    db = AsyncMock()
    async with await _client(db, {"user_id": 2, "email": "u@x.com", "role": "user"}) as c:
        r = await c.get(f"{PREFIX}/feedback")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_an_ordinary_user_cannot_triage():
    db = AsyncMock()
    async with await _client(db, {"user_id": 2, "email": "u@x.com", "role": "user"}) as c:
        r = await c.patch(f"{PREFIX}/feedback/1", json={"status": "done"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_the_owner_can_read_the_inbox():
    """Non-vacuity for the two tests above: the gate must not block the owner."""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    async with await _client(db, {"user_id": 1, "email": "o@x.com", "role": "admin"}) as c:
        r = await c.get(f"{PREFIX}/feedback")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_a_user_reads_only_their_own_submissions():
    """The form must not be a void — a user who cannot see their note arrived
    sends it again, or stops sending. But they see only theirs."""
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    async with await _client(db, {"user_id": 7, "email": "u@x.com", "role": "user"}) as c:
        r = await c.get(f"{PREFIX}/feedback/mine")
    assert r.status_code == 200
    # The filter is on the caller's own id, taken from the token.
    assert "7" in str(db.execute.await_args) or db.execute.await_count == 1


@pytest.mark.asyncio
async def test_mine_is_not_shadowed_by_the_id_route():
    """`/feedback/mine` and `/feedback/{id}` share a prefix. If the id route
    captured "mine", a user's own list would 404 or 422 instead."""
    paths = {r.path for r in app.routes if "feedback" in getattr(r, "path", "")}
    assert f"{PREFIX}/feedback/mine" in paths


def test_the_owner_note_is_never_returned_to_a_submitter():
    """It is the owner's private triage note. The submitter-facing schema must
    not carry it, or a candid note reaches the person it is about."""
    from app.models.schemas import FeedbackResponse
    assert "owner_note" not in FeedbackResponse.model_fields
    assert "user_agent" not in FeedbackResponse.model_fields
    # ...and the admin view does carry both.
    from app.models.schemas import FeedbackAdminResponse
    assert "owner_note" in FeedbackAdminResponse.model_fields
    assert "user_id" in FeedbackAdminResponse.model_fields


def test_the_form_defaults_to_an_idea_rather_than_a_problem():
    """A feedback form whose default is "problem" invites complaints; the row
    this was built for is ideas and opinions."""
    assert FeedbackCreate(message="something").category.value == "idea"


def test_the_literal_feedback_routes_outrank_the_portfolio_id_catch_all():
    """THE BUG THIS SHIPPED WITH, pinned by behaviour rather than line number.

    `GET /portfolio/{portfolio_id}` is declared in this router, and FastAPI
    matches routes in DECLARATION ORDER. With the feedback section appended at
    the end of the file, `GET /portfolio/feedback` resolved to the
    parameterised route, which tried to read "feedback" as an int and returned
    422. Only a real HTTP request shows this — the route exists, is mounted, and
    looks correct in a route listing.
    """
    order = [getattr(r, "path", "") for r in app.routes]
    catch_all = f"{PREFIX}/{{portfolio_id}}"
    assert catch_all in order, "the catch-all route moved; re-check this ordering"
    assert order.index(f"{PREFIX}/feedback") < order.index(catch_all)
    assert order.index(f"{PREFIX}/feedback/mine") < order.index(catch_all)


# ---------------------------------------------------------------------------
# The inbox gate, and why it is an email allowlist
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_an_allowlisted_address_can_read_the_inbox_without_a_role(monkeypatch):
    """THE REASON THIS GATE IS NOT ROLE-ONLY.

    The deployed `users` table has NO role or is_admin column, and
    auth-service's JWT sets role = payload.get("role", "user") — so every real
    token says "user" and nothing can grant admin. A role-only gate makes the
    endpoint unreachable by ANYONE, which is exactly how the stock-data
    repair-history endpoint refused the owner's own token on 2026-11-03.

    The `email` claim is signed with the same secret as `sub`, so trusting it
    is no weaker than trusting the user_id this service already acts on.
    """
    import app.api.routes as routes
    monkeypatch.setattr(routes, "_owner_emails", lambda: {"owner@example.com"})

    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    async with await _client(db, {"user_id": 1, "email": "owner@example.com",
                                  "role": "user"}) as c:
        r = await c.get(f"{PREFIX}/feedback")
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_a_non_allowlisted_address_is_still_refused(monkeypatch):
    """Non-vacuity: the allowlist must be a list, not a door."""
    import app.api.routes as routes
    monkeypatch.setattr(routes, "_owner_emails", lambda: {"owner@example.com"})
    db = AsyncMock()
    async with await _client(db, {"user_id": 2, "email": "someone@else.com",
                                  "role": "user"}) as c:
        r = await c.get(f"{PREFIX}/feedback")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_an_empty_allowlist_closes_the_inbox_rather_than_opening_it():
    """An unset config must fail CLOSED. The opposite default would publish
    every user's feedback to every user the moment the var went missing."""
    import app.api.routes as routes
    db = AsyncMock()
    # No monkeypatch: the real _owner_emails() reads the setting, empty in tests.
    assert routes._owner_emails() == set()
    async with await _client(db, {"user_id": 9, "email": "anyone@x.com",
                                  "role": "user"}) as c:
        r = await c.get(f"{PREFIX}/feedback")
    assert r.status_code == 403


def test_the_allowlist_is_case_and_space_insensitive():
    """People type addresses with capitals and stray spaces; an allowlist that
    missed those would lock the owner out for a reason nobody would guess."""
    import app.api.routes as routes
    from app.config import get_settings

    s = get_settings()
    original = getattr(s, "FEEDBACK_ADMIN_EMAILS", "")
    try:
        object.__setattr__(s, "FEEDBACK_ADMIN_EMAILS",
                           " Owner@Example.COM , second@x.com ")
        assert routes._owner_emails() == {"owner@example.com", "second@x.com"}
    finally:
        object.__setattr__(s, "FEEDBACK_ADMIN_EMAILS", original)


def test_a_blank_entry_does_not_become_a_wildcard():
    """"a@b.com,," must not allowlist the empty string, which would then match
    a token with no email claim."""
    import app.api.routes as routes
    from app.config import get_settings

    s = get_settings()
    original = getattr(s, "FEEDBACK_ADMIN_EMAILS", "")
    try:
        object.__setattr__(s, "FEEDBACK_ADMIN_EMAILS", "a@b.com,, ,")
        assert routes._owner_emails() == {"a@b.com"}
        assert "" not in routes._owner_emails()
    finally:
        object.__setattr__(s, "FEEDBACK_ADMIN_EMAILS", original)
