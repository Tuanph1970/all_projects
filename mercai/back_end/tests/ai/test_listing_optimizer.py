"""
Listing optimizer (docs/ai-features/02-listing-optimizer.md).

The behaviour that matters is not that suggestions get generated -- it is that
the model cannot fabricate attributes, cannot make safety or commercial
claims, and cannot write to the catalogue.
"""
import pytest

from shared.models.ai import AiSuggestion
from shared.models.product import Product


def suggestions(db):
    return db.query(AiSuggestion).order_by(AiSuggestion.id).all()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_suggest_returns_field_diffs(client, db, product):
    response = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id})

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["product_id"] == product.id
    assert body["cached"] is False
    assert body["suggestions"]["name"]["current"] == "blue vase"
    assert "Cobalt Blue" in body["suggestions"]["name"]["proposed"]
    # `current` travels with every proposal so the client renders a diff.
    assert body["suggestions"]["name"]["rationale"]


def test_proposal_is_recorded_for_measurement(client, db, product, seller):
    client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id})

    rows = suggestions(db)
    assert len(rows) == 1
    assert rows[0].feature == "listing_optimizer"
    assert rows[0].entity_type == "product"
    assert rows[0].entity_id == product.id
    assert rows[0].seller_id == seller.id
    assert rows[0].status == "proposed"
    # Pinned to the module constant rather than a literal: bumping the prompt
    # is expected, silently losing the version stamp is not.
    from app.prompts.listing import PROMPT_VERSION
    assert rows[0].prompt_version == PROMPT_VERSION


def test_duplicate_tags_are_deduplicated(client, product):
    body = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id}).json()
    tags = body["suggestions"]["tags"]["proposed"].split(",")
    assert tags == list(dict.fromkeys(tags))


# ---------------------------------------------------------------------------
# The core safety property: no catalogue writes
# ---------------------------------------------------------------------------

def test_suggesting_never_modifies_the_product(client, db, product):
    original_name = product.name
    original_material = product.material

    client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id})

    db.expire_all()
    fresh = db.query(Product).filter(Product.id == product.id).one()
    assert fresh.name == original_name
    assert fresh.material == original_material


# ---------------------------------------------------------------------------
# Anti-fabrication
# ---------------------------------------------------------------------------

def test_unsupported_attribute_becomes_a_question(client, db, product, stub_model):
    """
    The model claims a technique the seller never mentioned. It must not be
    offered as a value -- buyers filter on these fields.
    """
    stub_model["output"] = {
        "attributes": {
            "technique": {"proposed": "raku-fired", "rationale": "Looks like raku."},
        }
    }

    body = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id}).json()
    technique = body["suggestions"]["attributes"]["technique"]

    assert technique["proposed"] is None
    assert "ask_seller" in technique


def test_supported_attribute_is_offered(client, product, stub_model):
    """'stoneware' does appear in the seller's own description."""
    stub_model["output"] = {
        "attributes": {
            "material": {"proposed": "stoneware", "rationale": "Stated by the seller."},
        }
    }

    body = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id}).json()
    assert body["suggestions"]["attributes"]["material"]["proposed"] == "stoneware"


# ---------------------------------------------------------------------------
# Claim denylists
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("claim", [
    "This vase is food safe and dishwasher safe.",
    "The glaze is completely lead free.",
    "It is microwave safe for daily use.",
])
def test_safety_claims_are_stripped(client, product, stub_model, claim):
    stub_model["output"] = {
        "description": {"proposed": f"A hand-thrown vase. {claim}", "rationale": "x"},
    }

    body = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id}).json()
    proposed = body["suggestions"].get("description", {}).get("proposed", "")

    assert "safe" not in proposed.lower()
    assert "lead free" not in proposed.lower()
    assert "hand-thrown vase" in proposed.lower()


@pytest.mark.parametrize("claim", [
    "Get 20% off this week.",
    "Free shipping on all orders.",
    "Comes with a money-back guarantee.",
])
def test_commercial_claims_are_stripped(client, product, stub_model, claim):
    stub_model["output"] = {
        "description": {"proposed": f"A hand-thrown vase. {claim}", "rationale": "x"},
    }

    body = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id}).json()
    proposed = body["suggestions"].get("description", {}).get("proposed", "")

    for word in ("off", "free shipping", "guarantee"):
        assert word not in proposed.lower()


def test_price_is_never_suggested(client, product, stub_model):
    """`price` is not a field the optimizer may return, whatever the model says."""
    stub_model["output"] = {
        "price": {"proposed": "99.00", "rationale": "Underpriced."},
        "name": {"proposed": "A Better Name", "rationale": "x"},
    }

    body = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id}).json()
    assert "price" not in body["suggestions"]


# ---------------------------------------------------------------------------
# Authorisation and flags
# ---------------------------------------------------------------------------

def test_cannot_suggest_for_another_sellers_product(client, db, other_seller):
    from shared.models.product import Product as P

    rival = P(name="Rival vase", description="theirs", price=99,
              quantity_available=1, seller_id=other_seller.id, is_active=True)
    db.add(rival)
    db.commit()
    db.refresh(rival)

    response = client.post("/api/v1/ai/listing/suggest", json={"product_id": rival.id})
    assert response.status_code == 403


def test_missing_product_is_404(client):
    assert client.post("/api/v1/ai/listing/suggest", json={"product_id": 99999}).status_code == 404


def test_disabled_feature_returns_404(client, product, monkeypatch):
    """A disabled feature should not advertise its own existence."""
    from shared.config import settings
    monkeypatch.setattr(settings, "AI_LISTING_OPTIMIZER_ENABLED", False)

    response = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_model_unavailable_returns_503(client, db, product, stub_model):
    import app.services.ollama_client as ollama_module
    stub_model["error"] = ollama_module.OllamaUnavailable("model down")

    response = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id})

    assert response.status_code == 503
    assert "unaffected" in response.json()["detail"]
    # The failure is recorded so the error rate is measurable.
    assert suggestions(db)[0].error == "model down"


def test_model_busy_returns_429(client, product, stub_model):
    import app.services.ollama_client as ollama_module
    stub_model["error"] = ollama_module.OllamaBusy("saturated")

    response = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "15"


# ---------------------------------------------------------------------------
# Resolution (the acceptance metric)
# ---------------------------------------------------------------------------

def test_resolve_records_accepted_fields(client, db, product):
    suggestion_id = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": product.id}
    ).json()["suggestion_id"]

    response = client.post(
        f"/api/v1/ai/listing/suggestions/{suggestion_id}/resolve",
        json={"status": "partially_accepted", "accepted_fields": ["name", "tags"]},
    )

    assert response.status_code == 200
    db.expire_all()
    row = db.query(AiSuggestion).filter(AiSuggestion.id == suggestion_id).one()
    assert row.status == "partially_accepted"
    assert row.accepted_fields == ["name", "tags"]
    assert row.resolved_at is not None


def test_resolve_rejects_unknown_status(client, product):
    suggestion_id = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": product.id}
    ).json()["suggestion_id"]

    response = client.post(
        f"/api/v1/ai/listing/suggestions/{suggestion_id}/resolve",
        json={"status": "applied_automatically"},
    )
    assert response.status_code == 422


def test_cannot_resolve_another_sellers_suggestion(client, db, product, other_seller):
    suggestion_id = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": product.id}
    ).json()["suggestion_id"]

    row = db.query(AiSuggestion).filter(AiSuggestion.id == suggestion_id).one()
    row.seller_id = other_seller.id
    db.commit()

    response = client.post(
        f"/api/v1/ai/listing/suggestions/{suggestion_id}/resolve",
        json={"status": "accepted"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Draft mode -- suggestions before the listing is saved
# ---------------------------------------------------------------------------

DRAFT = {
    "name": "blue vase",
    "description": "a nice stoneware vase, hand-thrown, 24cm tall",
}


def test_draft_suggestion_needs_no_saved_product(client, db):
    """
    The create form has no product_id yet, and that is the highest-value moment
    for the optimizer -- so it must work without one.
    """
    response = client.post("/api/v1/ai/listing/suggest", json={"draft": DRAFT})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["product_id"] is None
    assert body["suggestions"]["name"]["proposed"]


def test_draft_creates_no_product_row(client, db):
    before = db.query(Product).count()
    client.post("/api/v1/ai/listing/suggest", json={"draft": DRAFT})
    db.expire_all()
    assert db.query(Product).count() == before


def test_draft_skips_the_image_report(client):
    """A draft's photos are still on the device; 'no images' would mislead."""
    body = client.post("/api/v1/ai/listing/suggest", json={"draft": DRAFT}).json()
    assert body["image_report"]["score"] == "not_applicable"
    assert body["image_report"]["findings"] == []


def test_draft_is_recorded_distinctly(client, db):
    client.post("/api/v1/ai/listing/suggest", json={"draft": DRAFT})
    row = suggestions(db)[0]
    assert row.entity_type == "draft"
    assert row.entity_id is None


def test_draft_still_enforces_anti_fabrication(client, stub_model):
    stub_model["output"] = {
        "attributes": {"technique": {"proposed": "raku-fired", "rationale": "guess"}}
    }
    body = client.post("/api/v1/ai/listing/suggest", json={"draft": DRAFT}).json()
    assert body["suggestions"]["attributes"]["technique"]["proposed"] is None


def test_must_supply_exactly_one_of_product_id_or_draft(client, product):
    both = client.post(
        "/api/v1/ai/listing/suggest",
        json={"product_id": product.id, "draft": DRAFT},
    )
    neither = client.post("/api/v1/ai/listing/suggest", json={})
    assert both.status_code == 422
    assert neither.status_code == 422


# ---------------------------------------------------------------------------
# Unsupported-claim guard: FLAG, don't block
# ---------------------------------------------------------------------------
#
# Distinct from the safety/commercial denylists above, which strip. Measured
# fabrication is ~1 in 4 on a near-empty listing and near zero on a complete
# one, so blocking would fire mostly on false positives.

def test_invented_use_is_flagged_not_removed(client, product, stub_model):
    """The exact failure seen against a live model on 2026-08-19."""
    stub_model["output"] = {
        "description": {
            "proposed": "A small earthenware bowl, crafted for everyday use.",
            "rationale": "x",
        }
    }

    body = client.post("/api/v1/ai/listing/suggest", json={"product_id": product.id}).json()
    entry = body["suggestions"]["description"]

    # The text survives -- the seller decides.
    assert "everyday use" in entry["proposed"]
    assert entry["unsupported"][0]["claims"] == ["everyday"]


def test_invented_finish_is_flagged(client, product, stub_model):
    """The v2 regression: a glaze finish the seller never mentioned."""
    stub_model["output"] = {
        "description": {
            "proposed": "A stoneware vase with a smooth matte glaze.",
            "rationale": "x",
        }
    }

    flagged = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": product.id}
    ).json()["suggestions"]["description"]["unsupported"]

    assert set(flagged[0]["claims"]) >= {"matte", "smooth"}


def test_connectives_are_not_flagged(client, product, stub_model):
    """
    'standing at 24cm' and 'a capacity of 300ml' assert nothing new. A naive
    unseen-word check flagged both and made the signal useless.
    """
    stub_model["output"] = {
        "description": {
            "proposed": "A hand-thrown stoneware vase, standing at 24cm tall.",
            "rationale": "x",
        }
    }

    entry = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": product.id}
    ).json()["suggestions"]["description"]

    assert "unsupported" not in entry


def test_claim_supported_by_seller_text_is_not_flagged(client, db, seller, stub_model):
    """If the seller already said 'matte', repeating it is not fabrication."""
    from shared.models.product import Product as P

    item = P(name="matte bowl", description="a matte glazed earthenware bowl",
             price=10, quantity_available=1, seller_id=seller.id, is_active=True)
    db.add(item); db.commit(); db.refresh(item)

    stub_model["output"] = {
        "description": {"proposed": "An earthenware bowl with a matte glaze.", "rationale": "x"}
    }

    entry = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": item.id}
    ).json()["suggestions"]["description"]

    assert "unsupported" not in entry


def test_flagging_is_per_sentence(client, product, stub_model):
    """Only the offending sentence is identified, so the seller can cut just it."""
    stub_model["output"] = {
        "description": {
            "proposed": "A hand-thrown stoneware vase, 24cm tall. Perfect as a gift.",
            "rationale": "x",
        }
    }

    flagged = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": product.id}
    ).json()["suggestions"]["description"]["unsupported"]

    assert len(flagged) == 1
    assert flagged[0]["sentence"] == "Perfect as a gift."


def test_safety_claims_are_still_blocked_not_flagged(client, product, stub_model):
    """The two mechanisms must not be confused: safety claims still get cut."""
    stub_model["output"] = {
        "description": {
            "proposed": "A stoneware vase. It is food safe and dishwasher safe.",
            "rationale": "x",
        }
    }

    entry = client.post(
        "/api/v1/ai/listing/suggest", json={"product_id": product.id}
    ).json()["suggestions"]["description"]

    assert "safe" not in entry["proposed"].lower()
