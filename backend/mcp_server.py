"""
Read-only LinkNodes MCP server (Streamable HTTP, mounted at /mcp).

Tools wrap the same in-process catalogs and feed reads as /v1.
No API keys. No writes. Runs inside the existing FastAPI process.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

mcp = MCPServer(
    name="LinkNodes",
    version="2.1.0",
    website_url="https://www.linknodes.io",
    instructions=(
        "Read-only Chainlink developer toolkit. Use these tools to look up Data Feeds, "
        "compare a feed across chains, inspect CCIP lanes, list 24/7 streams and operators, "
        "and read the cached Chainlink for Agents catalog. No keys required."
    ),
)

SEARCH_LIMIT_MAX = 25


def _ok(payload: Any) -> str:
    return json.dumps(payload, default=str)


def _err(message: str) -> str:
    return json.dumps({"error": message})


def _main():
    import main as engine

    return engine


def search_feeds_payload(
    query: str = "",
    network: str = "",
    environment: str = "mainnet",
    limit: int = 15,
) -> dict:
    engine = _main()
    env = (environment or "mainnet").lower()
    if env not in ("mainnet", "testnet"):
        return {"error": "environment must be 'mainnet' or 'testnet'"}
    limit = max(1, min(int(limit or 15), SEARCH_LIMIT_MAX))
    q = (query or "").strip().lower()
    net_filter = (network or "").strip().lower()
    registry = engine.get_registry(env)
    matches: list[dict] = []
    for net_slug, net in registry["networks"].items():
        if net_filter and net_slug != net_filter:
            continue
        visible = engine.filter_visible_feeds(net["feeds"])
        for slug, feed in visible.items():
            name = (feed.get("name") or "").lower()
            if q and q not in slug and q not in name:
                continue
            matches.append(
                {
                    "network": net_slug,
                    "network_label": net.get("label"),
                    "feed": slug,
                    "name": feed.get("name"),
                    "address": feed.get("address"),
                    "decimals": feed.get("decimals"),
                    "heartbeat": feed.get("heartbeat"),
                    "category": feed.get("category"),
                }
            )
            if len(matches) >= limit:
                return {"count": len(matches), "truncated": True, "results": matches}
    return {"count": len(matches), "truncated": False, "results": matches}


def ccip_lane_payload(source: str, destination: str, environment: str = "mainnet") -> dict:
    engine = _main()
    env = (environment or "mainnet").lower()
    if env not in ("mainnet", "testnet"):
        return {"error": "environment must be 'mainnet' or 'testnet'"}
    if not source or not destination:
        return {"error": "source and destination are required"}
    source_l = source.lower()
    dest_l = destination.lower()
    registry = engine.get_ccip_registry(env)
    source_net = registry["networks"].get(source_l)
    dest_net = registry["networks"].get(dest_l)
    if not source_net or not dest_net:
        alt = engine.get_ccip_registry("testnet" if env == "mainnet" else "mainnet")
        source_net = source_net or alt["networks"].get(source_l)
        dest_net = dest_net or alt["networks"].get(dest_l)
    if not source_net:
        return {"error": f"Unknown source network '{source}'."}
    if not dest_net:
        return {"error": f"Unknown destination network '{destination}'."}
    if dest_l not in source_net.get("supports", []):
        return {
            "error": (
                f"CCIP lane from {source_net['label']} to {dest_net['label']} "
                "is not supported or not yet enabled."
            )
        }
    return {
        "success": True,
        "lane": f"{source_l} → {dest_l}",
        "source": {
            "network": source_l,
            "label": source_net["label"],
            "chain_id": source_net["chain_id"],
            "chain_selector": source_net["chain_selector"],
            "router": source_net["router"],
            "rmn_proxy": source_net.get("rmn_proxy") or source_net.get("arm_proxy"),
        },
        "destination": {
            "network": dest_l,
            "label": dest_net["label"],
            "chain_id": dest_net["chain_id"],
            "chain_selector": dest_net["chain_selector"],
            "router": dest_net["router"],
            "rmn_proxy": dest_net.get("rmn_proxy") or dest_net.get("arm_proxy"),
        },
    }


@mcp.tool(description="Search the LinkNodes Data Feeds catalog by name, slug, or chain. Returns metadata only (no live price).")
def search_feeds(
    query: str = "",
    network: str = "",
    environment: str = "mainnet",
    limit: int = 15,
) -> str:
    return _ok(search_feeds_payload(query, network, environment, limit))


@mcp.tool(description="Live latestRoundData (or historical getRoundData) for one Chainlink Data Feed. network is a slug such as ethereum or base; feed is a slug such as eth-usd.")
async def lookup_feed(
    network: str,
    feed: str,
    round_id: int | None = None,
    environment: str = "mainnet",
) -> str:
    engine = _main()
    env = (environment or "mainnet").lower()
    if env not in ("mainnet", "testnet"):
        return _err("environment must be 'mainnet' or 'testnet'")
    if not network or not feed:
        return _err("network and feed are required")
    try:
        result = await engine._read_feed(network.lower(), feed.lower(), round_id, env)
        return _ok(result)
    except engine.HTTPException as exc:
        return _err(str(exc.detail))
    except Exception as exc:
        return _err(str(exc))


@mcp.tool(description="Query the same Data Feed on every chain it is deployed on and return per-chain prices plus spread_bps.")
async def compare_feed(feed: str, environment: str = "mainnet") -> str:
    engine = _main()
    env = (environment or "mainnet").lower()
    if env not in ("mainnet", "testnet"):
        return _err("environment must be 'mainnet' or 'testnet'")
    if not feed:
        return _err("feed is required")
    try:
        result = await engine.compare_feed(feed=feed.lower(), environment=env)
        return _ok(result)
    except engine.HTTPException as exc:
        return _err(str(exc.detail))
    except Exception as exc:
        return _err(str(exc))


@mcp.tool(description="List CCIP networks, routers, chain selectors, and supported destinations.")
def ccip_registry(environment: str = "mainnet") -> str:
    engine = _main()
    env = (environment or "mainnet").lower()
    if env not in ("mainnet", "testnet"):
        return _err("environment must be 'mainnet' or 'testnet'")
    return _ok(engine.get_ccip_registry(env))


@mcp.tool(description="Look up one CCIP lane (source -> destination): routers, selectors, RMN proxies.")
def ccip_lane(source: str, destination: str, environment: str = "mainnet") -> str:
    return _ok(ccip_lane_payload(source, destination, environment))


@mcp.tool(description="List-only catalog of Chainlink 24/7 Data Streams (feed IDs, no live report prices).")
def list_streams_247() -> str:
    return _ok(_main().STREAMS_247)


@mcp.tool(description="Curated directory of well-known Chainlink node operators.")
def list_operators() -> str:
    return _ok(_main().OPERATORS)


@mcp.tool(description="Cached Chainlink for Agents gateway catalog, including published USDC prices when the unpaid catalog document included them.")
def agents_catalog() -> str:
    return _ok(_main().get_agents_catalog())


def create_mcp_http_app():
    """Stateless JSON Streamable HTTP app, mounted at /mcp.

    DNS-rebinding protection is off: this is a public read-only API that must
    accept Host headers from App Runner, localhost, and TestClient.
    """
    return mcp.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
