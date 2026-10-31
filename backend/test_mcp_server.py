"""Tests for the in-process LinkNodes MCP tools and /mcp HTTP mount."""

from __future__ import annotations

import json
import os

os.environ.setdefault("LINKNODES_DISABLE_AGENTS_REFRESH", "1")

from fastapi.testclient import TestClient

from mcp_server import ccip_lane_payload, search_feeds_payload


def test_search_feeds_finds_eth_usd():
    result = search_feeds_payload(query="eth-usd", network="ethereum", limit=5)
    assert result["count"] >= 1
    assert any(item["feed"] == "eth-usd" and item["network"] == "ethereum" for item in result["results"])


def test_search_feeds_rejects_bad_environment():
    result = search_feeds_payload(environment="staging")
    assert "error" in result


def test_ccip_lane_ethereum_arbitrum():
    result = ccip_lane_payload("ethereum", "arbitrum")
    assert result.get("success") is True
    assert result["source"]["router"].startswith("0x")
    assert result["destination"]["chain_selector"]


def test_ccip_lane_unsupported():
    result = ccip_lane_payload("ethereum", "zksync")
    assert "error" in result
    assert "not supported" in result["error"].lower()


def test_mcp_http_initialize_and_tools_list():
    from main import app

    with TestClient(app) as client:
        noslash = client.post(
            "/mcp",
            follow_redirects=False,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "linknodes-test", "version": "0.0.1"},
                },
            },
        )
        assert noslash.status_code == 200, noslash.text

        init = client.post(
            "/mcp/",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "linknodes-test", "version": "0.0.1"},
                },
            },
        )
        assert init.status_code == 200, init.text
        body = init.json()
        assert body.get("result", {}).get("serverInfo", {}).get("name") == "LinkNodes"

        listed = client.post(
            "/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        assert listed.status_code == 200, listed.text
        names = {tool["name"] for tool in listed.json()["result"]["tools"]}
        assert {
            "search_feeds",
            "lookup_feed",
            "compare_feed",
            "ccip_registry",
            "ccip_lane",
            "list_streams_247",
            "list_operators",
            "agents_catalog",
        } <= names

        # Existing /v1 routes still work with MCP mounted.
        health = client.get("/healthz")
        assert health.status_code == 200
        registry = client.get("/v1/registry")
        assert registry.status_code == 200
        assert "networks" in registry.json()
