"""Trade diary + chart upload tests."""
import io

import pytest

from tests.conftest import API_PREFIX


@pytest.mark.asyncio
async def test_create_diary_for_trade(client, headers, trade):
    r = await client.post(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={
            "reasons_for_trade": "Strong volume confirmation",
            "chart_pattern": "Bull Flag",
            "emotional_state_entry": "Confident",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["trade_id"] == trade["id"]
    assert body["chart_pattern"] == "Bull Flag"
    assert body["emotional_state_entry"] == "Confident"


@pytest.mark.asyncio
async def test_create_diary_is_idempotent(client, headers, trade):
    """POST /diary acts as get-or-create — calling twice should not 500."""
    first = await client.post(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={"reasons_for_trade": "first take"},
        headers=headers,
    )
    second = await client.post(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={"reasons_for_trade": "second call"},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code in (200, 201)
    assert second.json()["id"] == first.json()["id"]


@pytest.mark.asyncio
async def test_diary_404_for_other_user(client, headers, other_user_headers, trade):
    await client.post(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={"reasons_for_trade": "owner only"},
        headers=headers,
    )
    r = await client.get(
        f"{API_PREFIX}/trades/{trade['id']}/diary", headers=other_user_headers
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_diary_with_lessons(client, headers, account, trade):
    """Schwager's rule: outcome/lessons may only be filled after trade is closed.
    Verify both halves: 400 while open, 200 once closed."""
    await client.post(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={"reasons_for_trade": "Initial entry"},
        headers=headers,
    )

    # While the trade is still open, "how_it_turned_out" is rejected.
    too_early = await client.put(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={"how_it_turned_out": "Stopped out at 95"},
        headers=headers,
    )
    assert too_early.status_code == 400

    # Close the trade, then the same fields are accepted.
    closed = await client.post(
        f"{API_PREFIX}/accounts/{account['id']}/trades/{trade['id']}/close?exit_price=95",
        headers=headers,
    )
    assert closed.status_code == 200

    r = await client.put(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={
            "how_it_turned_out": "Stopped out at 95",
            "lessons_and_mistakes": "Position size was too aggressive",
            "emotional_state_during": "Anxious",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["how_it_turned_out"] == "Stopped out at 95"
    assert body["emotional_state_during"] == "Anxious"


# ---------------------------------------------------------------------------
# Chart upload
# ---------------------------------------------------------------------------

PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f"
    b"\x00\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.asyncio
async def test_upload_chart_validates_content_type(client, headers, trade):
    diary = (await client.post(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={"reasons_for_trade": "for chart upload"}, headers=headers,
    )).json()
    diary_id = diary["id"]

    bogus = await client.post(
        f"{API_PREFIX}/diary/{diary_id}/charts",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
        headers=headers,
    )
    assert bogus.status_code == 400


@pytest.mark.asyncio
async def test_upload_chart_succeeds_for_png(client, headers, trade, tmp_path, monkeypatch):
    # Redirect uploads to a tmp dir so we don't write into /app/uploads on the host.
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

    diary_resp = await client.post(
        f"{API_PREFIX}/trades/{trade['id']}/diary",
        json={"reasons_for_trade": "for chart upload"}, headers=headers,
    )
    assert diary_resp.status_code == 201
    diary_id = diary_resp.json()["id"]

    r = await client.post(
        f"{API_PREFIX}/diary/{diary_id}/charts",
        files={"file": ("entry.png", io.BytesIO(PNG_1x1), "image/png")},
        data={"caption": "Entry zone", "chart_type": "Entry"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["caption"] == "Entry zone"
    assert body["chart_type"] == "Entry"

    listed = await client.get(
        f"{API_PREFIX}/diary/{diary_id}/charts", headers=headers
    )
    assert listed.status_code == 200
    assert any(c["id"] == body["id"] for c in listed.json())
