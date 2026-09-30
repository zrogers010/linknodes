"""
LinkNodes Core Engine
=====================
The query engine behind the "Postman for Chainlink developers".

Stateless and un-gated: every request is a set of concurrent read-only
`eth_call`s against free-tier public RPCs. No database, no node, no accounts.
The full Chainlink Data Feeds catalog (generated from Chainlink's own
reference-data directory by `build_registry.py`) lives in `registry.json`,
loaded into memory at boot for O(1) lookups.

Production posture (still zero infrastructure):
- Micro-cache: latest-round responses are cached in-memory for a few seconds,
  historical rounds for an hour (they are immutable). This bounds upstream RPC
  load to O(feeds) instead of O(users).
- Rate limit: a small per-IP sliding window keeps abusive clients from burning
  shared public-RPC goodwill. Generous enough that no human ever sees it.
"""

import asyncio
import json
import time
from collections import defaultdict, deque
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from web3 import AsyncWeb3

REGISTRY_PATH = Path(__file__).parent / "registry.json"
REGISTRY: dict = json.loads(REGISTRY_PATH.read_text())

OPERATORS_PATH = Path(__file__).parent / "operators.json"
OPERATORS: dict = json.loads(OPERATORS_PATH.read_text())

RPC_TIMEOUT_S = 8.0
LATEST_CACHE_TTL_S = 5.0       # Chainlink updates on heartbeat/deviation; 5s loses nothing
HISTORICAL_CACHE_TTL_S = 3600  # past rounds never change
RATE_LIMIT_WINDOW_S = 60
RATE_LIMIT_MAX_REQUESTS = 120

# Minimal view-only AggregatorV3 ABI: live reads, historical rounds, metadata.
CHAINLINK_ABI = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint80", "name": "_roundId", "type": "uint80"}],
        "name": "getRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "description",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "version",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Aggregator metadata is immutable per proxy version; memoizing it keeps
# repeat queries at a single eth_call without any persistence layer.
_static_meta_cache: dict[tuple[str, str], tuple[int, str, int]] = {}

# (network, feed, round_id) -> (expires_at_monotonic, response_dict)
_response_cache: dict[tuple[str, str, int | None], tuple[float, dict]] = {}

# ip -> recent request timestamps (monotonic)
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)

app = FastAPI(
    title="LinkNodes Core Engine",
    version="2.1.0",
    description="The Postman for Chainlink developers. No keys, no accounts, no limits.",
)

# Universal CORS: the sandbox is a public utility, callable from anywhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# The full-catalog registry is ~450 KB raw; gzip ships it in ~15% of that.
app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith("/v1/"):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = _rate_buckets[ip]
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_S:
            bucket.popleft()
        if len(_rate_buckets) > 10000:
            for stale_ip in [k for k, v in _rate_buckets.items() if not v or now - v[-1] > RATE_LIMIT_WINDOW_S]:
                del _rate_buckets[stale_ip]
        if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded (120 requests/min). The API is free; please pace your calls."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_S)},
            )
        bucket.append(now)
    return await call_next(request)


def _resolve(network: str, feed: str) -> tuple[dict, dict]:
    net = REGISTRY["networks"].get(network.lower())
    if not net:
        raise HTTPException(status_code=400, detail=f"Unknown network '{network}'.")
    feed_meta = net["feeds"].get(feed.lower())
    if not feed_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Chainlink does not publish a '{feed}' feed on {net['label']}.",
        )
    return net, feed_meta


async def _read_feed(network: str, feed: str, round_id: int | None) -> dict:
    """Core read path: micro-cache, then concurrent eth_calls with RPC failover."""
    cache_entry = _response_cache.get((network, feed, round_id))
    if cache_entry and cache_entry[0] > time.monotonic():
        cached = dict(cache_entry[1])
        cached["meta"] = {**cached["meta"], "cache": "hit"}
        return cached

    net, feed_meta = _resolve(network, feed)
    address = feed_meta["address"]

    last_error: Exception | None = None
    for rpc_url in net["rpc_urls"]:
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": RPC_TIMEOUT_S}))
        contract = w3.eth.contract(address=w3.to_checksum_address(address), abi=CHAINLINK_ABI)
        round_fn = (
            contract.functions.getRoundData(round_id)
            if round_id is not None
            else contract.functions.latestRoundData()
        )
        meta_key = (network, feed)
        try:
            started = time.perf_counter()
            if meta_key in _static_meta_cache:
                decimals, description, agg_version = _static_meta_cache[meta_key]
                round_data = await round_fn.call()
            else:
                decimals, description, agg_version, round_data = await asyncio.gather(
                    contract.functions.decimals().call(),
                    contract.functions.description().call(),
                    contract.functions.version().call(),
                    round_fn.call(),
                )
                _static_meta_cache[meta_key] = (decimals, description, agg_version)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        except Exception as exc:
            # A revert is a deterministic contract answer (e.g. a round that
            # never existed), not an infrastructure failure -- don't fail over.
            if round_id is not None and "revert" in str(exc).lower():
                raise HTTPException(
                    status_code=404,
                    detail=f"The aggregator reverted for round_id={round_id}. Round IDs encode "
                    "the proxy phase in the upper 16 bits; use a roundId returned by a "
                    "previous latestRoundData() call.",
                )
            last_error = exc
            continue  # RPC flake -> fail over to the next public node

        rid, answer, started_at, updated_at, answered_in_round = round_data
        if round_id is not None and updated_at == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Round {round_id} does not exist on this aggregator phase. "
                "Round IDs encode the proxy phase in the upper 16 bits; try a roundId "
                "returned by a previous latestRoundData() call.",
            )

        response = {
            "success": True,
            "provider": "chainlink",
            "query_type": "historical_round" if round_id is not None else "latest_round",
            "meta": {
                "network": network,
                "chain_id": net["chain_id"],
                "feed_name": feed_meta["name"],
                "contract_address": address,
                "explorer_url": f"{net['explorer']}/address/{address}",
                "onchain_description": description,
                "decimals": decimals,
                "aggregator_version": agg_version,
                "feed_type": feed_meta["feed_type"],
                "risk_category": feed_meta["category"],
                "heartbeat_seconds": feed_meta["heartbeat"],
                "deviation_threshold_pct": feed_meta["deviation_threshold_pct"],
                "market_hours": feed_meta["market_hours"],
                "rpc_endpoint": rpc_url,
                "rpc_latency_ms": elapsed_ms,
                "cache": "miss",
            },
            "payload": {
                "price": answer / (10**decimals),
                "raw_integer": str(answer),
                "round_id": str(rid),
                "answered_in_round": str(answered_in_round),
                "started_at": started_at,
                "unix_timestamp": updated_at,
                "staleness_seconds": max(0, int(time.time()) - updated_at),
            },
        }
        ttl = HISTORICAL_CACHE_TTL_S if round_id is not None else LATEST_CACHE_TTL_S
        _response_cache[(network, feed, round_id)] = (time.monotonic() + ttl, response)
        if len(_response_cache) > 8192:
            now = time.monotonic()
            for key in [k for k, (exp, _) in _response_cache.items() if exp <= now]:
                del _response_cache[key]
        return response

    raise HTTPException(status_code=502, detail=f"All public RPC nodes failed for {network}: {last_error}")


@app.get("/v1/registry")
async def get_registry():
    """Full static catalog so the frontend renders every selector from one source of truth."""
    return REGISTRY


@app.get("/v1/query/{network}/{feed}")
async def query_feed(
    network: str,
    feed: str,
    round_id: int | None = Query(
        None,
        ge=0,
        description="Optional historical roundId for getRoundData(); omit for latestRoundData().",
    ),
):
    return await _read_feed(network.lower(), feed.lower(), round_id)


@app.get("/v1/compare/{feed}")
async def compare_feed(feed: str):
    """Query a feed on every chain it is deployed on, concurrently, and
    summarize the cross-chain spread."""
    feed = feed.lower()
    networks = [key for key, net in REGISTRY["networks"].items() if feed in net["feeds"]]
    if not networks:
        raise HTTPException(status_code=404, detail=f"No chain publishes a '{feed}' feed.")

    async def read_one(network: str) -> dict:
        try:
            r = await _read_feed(network, feed, None)
            return {
                "network": network,
                "network_label": REGISTRY["networks"][network]["label"],
                "success": True,
                "price": r["payload"]["price"],
                "unix_timestamp": r["payload"]["unix_timestamp"],
                "staleness_seconds": r["payload"]["staleness_seconds"],
                "contract_address": r["meta"]["contract_address"],
                "explorer_url": r["meta"]["explorer_url"],
                "rpc_latency_ms": r["meta"]["rpc_latency_ms"],
                "cache": r["meta"]["cache"],
            }
        except HTTPException as exc:
            return {
                "network": network,
                "network_label": REGISTRY["networks"][network]["label"],
                "success": False,
                "error": exc.detail,
            }

    started = time.perf_counter()
    results = await asyncio.gather(*(read_one(n) for n in networks))
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    ok = [r for r in results if r["success"]]
    summary: dict = {"chains_queried": len(results), "chains_ok": len(ok), "total_latency_ms": elapsed_ms}
    if len(ok) >= 2:
        lo = min(ok, key=lambda r: r["price"])
        hi = max(ok, key=lambda r: r["price"])
        mid = (lo["price"] + hi["price"]) / 2
        summary.update(
            {
                "min": {"network": lo["network"], "price": lo["price"]},
                "max": {"network": hi["network"], "price": hi["price"]},
                "spread_bps": round((hi["price"] - lo["price"]) / mid * 10000, 2) if mid else 0,
            }
        )

    return {"success": True, "feed": feed, "summary": summary, "results": results}


@app.get("/v1/operators")
async def get_operators():
    """Curated directory of well-known Chainlink node operators."""
    return OPERATORS


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "registry_version": REGISTRY["version"],
        "networks": len(REGISTRY["networks"]),
        "feeds": sum(n["feed_count"] for n in REGISTRY["networks"].values()),
        "cache_entries": len(_response_cache),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)
