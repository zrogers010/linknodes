"""Tests for the cached Chainlink for Agents catalog."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from build_agents_catalog import (
    empty_catalog,
    normalize_item,
    refresh_catalog,
    should_keep_last_good,
    validate_catalog,
)

BACKEND = Path(__file__).parent
os.environ.setdefault("LINKNODES_DISABLE_AGENTS_REFRESH", "1")


def _workflow_fixture(**overrides):
    item = {
        "name": "token-transfer",
        "description": "Build ERC-20 transfer calldata.",
        "kind": "workflow",
        "price_usdc": "0.01",
        "chain_selector_price_overrides_usdc": {"5009297550715157269": "0.05"},
        "execute_endpoint": "POST /v1/operations/token-transfer",
        "input_schema": {
            "amount": {"type": "string", "required": True},
            "chain_selector": {"type": "chain_selector", "required": True},
        },
    }
    item.update(overrides)
    return item


def test_normalize_keeps_published_price_and_labeled_override():
    item = normalize_item(
        _workflow_fixture(),
        {"5009297550715157269": "Ethereum Mainnet"},
    )
    assert item["price_usdc"] == "0.01"
    assert item["price_overrides"] == [
        {
            "chain_selector": "5009297550715157269",
            "price_usdc": "0.05",
            "network_label": "Ethereum Mainnet",
        }
    ]
    assert [p["name"] for p in item["input_params"]] == ["amount", "chain_selector"]


def test_normalize_omits_price_when_gateway_did_not_publish_one():
    item = normalize_item(
        {
            "name": "streams-latest-report",
            "description": "Get the latest signed Data Streams report.",
            "kind": "endpoint",
            "price_tier": "read",
            "execute_endpoint": "GET /v1/streams/reports/latest",
        },
        {},
    )
    assert item["price_usdc"] is None
    assert item["price_tier"] == "read"
    assert item["price_overrides"] == []


def test_validate_catalog_rejects_empty():
    with pytest.raises(RuntimeError):
        validate_catalog(empty_catalog())


def test_should_keep_last_good_on_shrink():
    previous = {
        "version": "1.0.0",
        "count": 10,
        "workflows": [{"name": f"w{i}"} for i in range(10)],
    }
    new = {
        "version": "1.0.0",
        "count": 2,
        "workflows": [{"name": "a"}, {"name": "b"}],
    }
    assert should_keep_last_good(new, previous)


def test_refresh_keeps_last_good_on_fetch_failure(tmp_path):
    output = tmp_path / "agents_catalog.json"
    existing = {
        "version": "1.0.0",
        "source": "chainlink-agents-gateway",
        "source_url": "https://agents.chain.link/v1/catalog",
        "generated_at": "2026-01-01T00:00:00Z",
        "status": "ok",
        "count": 1,
        "workflows": [{"name": "token-transfer", "description": "kept"}],
    }
    output.write_text(json.dumps(existing))
    before = output.read_text()

    with patch("build_agents_catalog.build_catalog", side_effect=RuntimeError("gateway down")):
        rc = refresh_catalog(output, tmp_path / "missing_ccip.json", strict=False)

    assert rc == 0
    assert output.read_text() == before


def test_committed_catalog_shape():
    path = BACKEND / "agents_catalog.json"
    assert path.exists(), "agents_catalog.json must be committed as the last-good copy"
    catalog = json.loads(path.read_text())
    validate_catalog(catalog)
    assert catalog["source_url"] == "https://agents.chain.link/v1/catalog"
    names = [w["name"] for w in catalog["workflows"]]
    assert "token-transfer" in names
    assert "streams-latest-report" in names
    for item in catalog["workflows"]:
        if item["name"].startswith("streams-"):
            assert item["price_usdc"] is None
        if item["name"] == "token-transfer":
            assert item["price_usdc"] == "0.01"


def test_agents_catalog_route_and_openapi():
    from main import app

    with TestClient(app) as client:
        catalog = client.get("/v1/agents/catalog")
        assert catalog.status_code == 200
        body = catalog.json()
        assert body["count"] >= 1
        assert isinstance(body["workflows"], list)

        spec = client.get("/v1/openapi.json")
        assert spec.status_code == 200
        openapi = spec.json()
        assert openapi["openapi"].startswith("3.")
        assert "/v1/agents/catalog" in openapi["paths"]
        assert "/v1/registry" in openapi["paths"]
        assert client.get("/openapi.json").status_code == 404

        health = client.get("/healthz")
        assert health.status_code == 200
        assert "agents_catalog" in health.json()
